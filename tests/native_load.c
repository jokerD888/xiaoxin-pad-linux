#include <dlfcn.h>
#include <stdio.h>
#include <assert.h>
int main(int argc,char **argv) {
    assert(argc==3);
    void *policy=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    if (!policy) { fprintf(stderr,"policy load: %s\n",dlerror());return 1; }
    int (*disable)(void*,void*)=dlsym(policy,"Java_com_anland_consumer_AudioPolicy_disableMMap");
    assert(disable);
    int result=disable(NULL,NULL);
    assert(result==0);
    void *native=dlopen(argv[2],RTLD_NOW|RTLD_LOCAL);
    if (!native) { fprintf(stderr,"native load: %s\n",dlerror());return 1; }
    void *audio=dlopen("libaaudio.so",RTLD_NOW|RTLD_LOCAL);
    int (*get_policy)(void)=dlsym(audio,"AAudio_getMMapPolicy");
    assert(get_policy && get_policy()==1);
    puts("PASS: native library loads; process-local MMAP policy remains NEVER");
    dlclose(audio);dlclose(native);dlclose(policy);
    return 0;
}
