/* Expose Anland NV21 cameras as I420 PipeWire sources for WebRTC.
 * Build: cc -O2 -Wall anland-camera-bridge.c -o anland-camera-bridge
 *        $(pkg-config --cflags --libs libpipewire-0.3)
 * Usage: anland-camera-bridge SOURCE WIDTH HEIGHT [OUTPUT_WIDTH OUTPUT_HEIGHT]
 * Source dimensions must match its PipeWire EnumFormat. No V4L2/kernel changes.
 */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pipewire/pipewire.h>
#include <spa/param/video/format-utils.h>

struct bridge {
  struct pw_main_loop *loop;
  struct pw_stream *input, *output;
  struct pw_context *context;
  struct pw_core *core;
  struct pw_registry *registry;
  struct spa_hook registry_listener;
  uint32_t links[128];
  unsigned consumers;
  unsigned sw, sh, dw, dh, stride;
  size_t bytes;
  uint8_t *frame;
  unsigned long received, sent;
  bool ready, failed;
};

static void stop(void *data, int sig) {
  (void)sig;
  pw_main_loop_quit(((struct bridge *)data)->loop);
}

static void input_state(void *data, enum pw_stream_state old,
                        enum pw_stream_state state, const char *error) {
  struct bridge *b=data;
  (void)old;
  fprintf(stderr,"input: %s %s\n",pw_stream_state_as_string(state),error?error:"");
  if(state==PW_STREAM_STATE_ERROR) {b->failed=true;pw_main_loop_quit(b->loop);}
}

static void output_state(void *data, enum pw_stream_state old,
                         enum pw_stream_state state, const char *error) {
  struct bridge *b=data;
  (void)old;
  fprintf(stderr,"output: %s %s\n",pw_stream_state_as_string(state),error?error:"");
  if(state==PW_STREAM_STATE_ERROR) {b->failed=true;pw_main_loop_quit(b->loop);return;}
  /* Android opens a sensor only while an application consumes this source. */
  if(b->input) pw_stream_set_active(b->input,state==PW_STREAM_STATE_STREAMING&&b->consumers>0);
  if(state!=PW_STREAM_STATE_STREAMING) b->ready=false;
}

static void input_format(void *data,uint32_t id,const struct spa_pod *pod) {
  struct bridge *b=data;
  if(id!=SPA_PARAM_Format||!pod)return;
  struct spa_video_info_raw info={0};
  if(spa_format_video_raw_parse(pod,&info)<0)return;
  if(info.format!=SPA_VIDEO_FORMAT_NV21||info.size.width!=b->sw||info.size.height!=b->sh) {
    fprintf(stderr,"unexpected input format\n");b->failed=true;pw_main_loop_quit(b->loop);return;
  }
  b->stride=b->sw;
}

static void output_format(void *data,uint32_t id,const struct spa_pod *pod) {
  struct bridge *b=data;
  if(id!=SPA_PARAM_Format||!pod)return;
  uint8_t mem[512];struct spa_pod_builder builder=SPA_POD_BUILDER_INIT(mem,sizeof(mem));
  const struct spa_pod *params[1];
  params[0]=spa_pod_builder_add_object(&builder,SPA_TYPE_OBJECT_ParamBuffers,SPA_PARAM_Buffers,
    SPA_PARAM_BUFFERS_buffers,SPA_POD_CHOICE_RANGE_Int(4,2,8),
    SPA_PARAM_BUFFERS_blocks,SPA_POD_Int(1),
    SPA_PARAM_BUFFERS_size,SPA_POD_Int(b->bytes),
    SPA_PARAM_BUFFERS_stride,SPA_POD_Int(b->dw),
    SPA_PARAM_BUFFERS_dataType,SPA_POD_CHOICE_FLAGS_Int((1<<SPA_DATA_MemPtr)|(1<<SPA_DATA_MemFd)));
  pw_stream_update_params(b->output,params,1);
}

static void output_process(void *data) {
  struct bridge *b=data;
  struct pw_buffer *out=pw_stream_dequeue_buffer(b->output);
  if(!out)return;
  struct spa_data *d=&out->buffer->datas[0];
  if(b->ready&&d->data&&d->maxsize>=b->bytes) {
    memcpy(d->data,b->frame,b->bytes);
    d->chunk->offset=0;d->chunk->size=b->bytes;d->chunk->stride=b->dw;
    out->size=1;
    ++b->sent;
  } else {d->chunk->offset=0;d->chunk->size=0;out->size=0;}
  pw_stream_queue_buffer(b->output,out);
}

static void input_process(void *data) {
  struct bridge *b=data;
  struct pw_buffer *in=pw_stream_dequeue_buffer(b->input);
  if(!in)return;
  struct spa_data *d=&in->buffer->datas[0];
  unsigned stride=d->chunk&&d->chunk->stride>0?(unsigned)d->chunk->stride:b->stride;
  size_t needed=(size_t)stride*b->sh*3/2;
  if(d->data&&d->chunk&&stride>=b->sw&&d->chunk->offset<=d->maxsize&&
     needed<=d->maxsize-d->chunk->offset&&d->chunk->size>=needed) {
    const uint8_t *y=(const uint8_t*)d->data+d->chunk->offset;
    const uint8_t *vu=y+(size_t)stride*b->sh;
    uint8_t *dy=b->frame,*du=dy+(size_t)b->dw*b->dh,*dv=du+(size_t)b->dw*b->dh/4;
    /* Downsample without allocating full-resolution intermediate frames.
     * All current Anland sensors have the same 4:3 aspect ratio. */
    for(unsigned row=0;row<b->dh;row++) {
      const uint8_t *src=y+(size_t)(row*b->sh/b->dh)*stride;
      for(unsigned col=0;col<b->dw;col++)dy[(size_t)row*b->dw+col]=src[col*b->sw/b->dw];
    }
    for(unsigned row=0;row<b->dh/2;row++) {
      const uint8_t *src=vu+(size_t)(row*b->sh/b->dh)*stride;
      for(unsigned col=0;col<b->dw/2;col++) {
        unsigned x=(col*b->sw/b->dw)*2;size_t at=(size_t)row*(b->dw/2)+col;
        dv[at]=src[x];du[at]=src[x+1];
      }
    }
    b->ready=true;
    if(++b->received==1)fprintf(stderr,"first real frame: %u x %u NV21 -> %u x %u I420\n",b->sw,b->sh,b->dw,b->dh);
    pw_stream_trigger_process(b->output);
  }
  pw_stream_queue_buffer(b->input,in);
}

static const struct pw_stream_events input_events={PW_VERSION_STREAM_EVENTS,
  .state_changed=input_state,.param_changed=input_format,.process=input_process};
static const struct pw_stream_events output_events={PW_VERSION_STREAM_EVENTS,
  .state_changed=output_state,.param_changed=output_format,.process=output_process};

static void registry_global(void *data,uint32_t id,uint32_t permissions,
                            const char *type,uint32_t version,const struct spa_dict *props) {
  struct bridge *b=data;
  (void)permissions;(void)version;
  if(strcmp(type,PW_TYPE_INTERFACE_Link)||!props||!b->output)return;
  const char *source=spa_dict_lookup(props,PW_KEY_LINK_OUTPUT_NODE);
  if(!source||strtoul(source,NULL,10)!=pw_stream_get_node_id(b->output))return;
  if(b->consumers>=128)return;
  b->links[b->consumers++]=id;
  fprintf(stderr,"camera consumers: %u\n",b->consumers);
  if(pw_stream_get_state(b->output,NULL)==PW_STREAM_STATE_STREAMING)
    pw_stream_set_active(b->input,true);
}

static void registry_remove(void *data,uint32_t id) {
  struct bridge *b=data;
  for(unsigned i=0;i<b->consumers;i++) {
    if(b->links[i]!=id)continue;
    b->links[i]=b->links[--b->consumers];
    fprintf(stderr,"camera consumers: %u\n",b->consumers);
    if(!b->consumers) {pw_stream_set_active(b->input,false);b->ready=false;}
    break;
  }
}
static const struct pw_registry_events registry_events={PW_VERSION_REGISTRY_EVENTS,
  .global=registry_global,.global_remove=registry_remove};

int main(int argc,char **argv) {
  if(argc!=4&&argc!=6) {fprintf(stderr,"Usage: %s SOURCE WIDTH HEIGHT [OUTPUT_WIDTH OUTPUT_HEIGHT]\n",argv[0]);return 2;}
  struct bridge b={0};
  b.sw=strtoul(argv[2],NULL,10);b.sh=strtoul(argv[3],NULL,10);
  b.dw=argc==6?strtoul(argv[4],NULL,10):1280;b.dh=argc==6?strtoul(argv[5],NULL,10):960;
  if(!b.sw||!b.sh||!b.dw||!b.dh||(b.sw|b.sh|b.dw|b.dh)&1||
     b.sw>8192||b.sh>8192||b.dw>b.sw||b.dh>b.sh||b.sw*b.dh!=b.sh*b.dw) {
    fprintf(stderr,"Dimensions must be even, <=8192, and preserve the source aspect ratio\n");return 2;
  }
  b.stride=b.sw;b.bytes=(size_t)b.dw*b.dh*3/2;b.frame=calloc(1,b.bytes);
  if(!b.frame)return 1;
  pw_init(&argc,&argv);b.loop=pw_main_loop_new(NULL);
  if(!b.loop){free(b.frame);return 1;}
  pw_loop_add_signal(pw_main_loop_get_loop(b.loop),SIGINT,stop,&b);
  pw_loop_add_signal(pw_main_loop_get_loop(b.loop),SIGTERM,stop,&b);
  char name[256],description[256];
  snprintf(name,sizeof(name),"%s-webrtc",argv[1]);
  snprintf(description,sizeof(description),"Anland camera %s (WebRTC I420)",strrchr(argv[1],'-')?strrchr(argv[1],'-')+1:argv[1]);
  b.input=pw_stream_new_simple(pw_main_loop_get_loop(b.loop),"Anland NV21 capture",
    pw_properties_new(PW_KEY_MEDIA_TYPE,"Video",PW_KEY_MEDIA_CATEGORY,"Capture",PW_KEY_MEDIA_ROLE,"Camera",
      PW_KEY_TARGET_OBJECT,argv[1],PW_KEY_NODE_NAME,"anland-camera-bridge-capture",NULL),&input_events,&b);
  b.output=pw_stream_new_simple(pw_main_loop_get_loop(b.loop),"Anland WebRTC camera",
    pw_properties_new(PW_KEY_MEDIA_TYPE,"Video",PW_KEY_MEDIA_CATEGORY,"Capture",PW_KEY_MEDIA_ROLE,"Camera",
      PW_KEY_MEDIA_CLASS,"Video/Source",PW_KEY_NODE_NAME,name,PW_KEY_NODE_DESCRIPTION,description,
      PW_KEY_NODE_VIRTUAL,"true",NULL),&output_events,&b);
  if(!b.input||!b.output){b.failed=true;goto cleanup;}
  b.context=pw_context_new(pw_main_loop_get_loop(b.loop),NULL,0);
  if(!b.context){b.failed=true;goto cleanup;}
  b.core=pw_context_connect(b.context,NULL,0);
  if(!b.core){b.failed=true;goto cleanup;}
  b.registry=pw_core_get_registry(b.core,PW_VERSION_REGISTRY,0);
  pw_registry_add_listener(b.registry,&b.registry_listener,&registry_events,&b);
  uint8_t mem[1024];struct spa_pod_builder builder=SPA_POD_BUILDER_INIT(mem,sizeof(mem));
  const struct spa_pod *param=spa_format_video_raw_build(&builder,SPA_PARAM_EnumFormat,
    &(struct spa_video_info_raw){.format=SPA_VIDEO_FORMAT_NV21,.size={b.sw,b.sh},.framerate={30,1}});
  int result=pw_stream_connect(b.input,PW_DIRECTION_INPUT,PW_ID_ANY,
    PW_STREAM_FLAG_AUTOCONNECT|PW_STREAM_FLAG_MAP_BUFFERS|PW_STREAM_FLAG_INACTIVE,&param,1);
  if(result<0){b.failed=true;goto cleanup;}
  builder=SPA_POD_BUILDER_INIT(mem,sizeof(mem));
  param=spa_format_video_raw_build(&builder,SPA_PARAM_EnumFormat,
    &(struct spa_video_info_raw){.format=SPA_VIDEO_FORMAT_I420,.size={b.dw,b.dh},.framerate={30,1}});
  result=pw_stream_connect(b.output,PW_DIRECTION_OUTPUT,PW_ID_ANY,
    PW_STREAM_FLAG_MAP_BUFFERS|PW_STREAM_FLAG_TRIGGER,&param,1);
  if(result<0){b.failed=true;goto cleanup;}
  fprintf(stderr,"registered %s; waiting for a camera consumer\n",name);
  pw_main_loop_run(b.loop);
cleanup:
  fprintf(stderr,"received=%lu sent=%lu\n",b.received,b.sent);
  if(b.output)pw_stream_destroy(b.output);
  if(b.input)pw_stream_destroy(b.input);
  if(b.registry){spa_hook_remove(&b.registry_listener);pw_proxy_destroy((struct pw_proxy*)b.registry);}
  if(b.core)pw_core_disconnect(b.core);
  if(b.context)pw_context_destroy(b.context);
  pw_main_loop_destroy(b.loop);pw_deinit();free(b.frame);
  return b.failed?1:0;
}
