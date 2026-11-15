#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/mman.h>
#include <unistd.h>
#include <wayland-client.h>

#include "xdg-shell-client-protocol.h"
#include "viewporter-client-protocol.h"

#define LOCK_FILE "/run/user/1000/black-screen-saver.lock"

struct app_state {
    struct wl_display *display;
    struct wl_registry *registry;
    struct wl_compositor *compositor;
    struct wl_shm *shm;
    struct wl_seat *seat;
    struct wl_pointer *pointer;
    struct wl_keyboard *keyboard;
    struct wl_touch *touch;
    struct xdg_wm_base *wm_base;
    struct wp_viewporter *viewporter;

    struct wl_surface *surface;
    struct xdg_surface *xdg_surface;
    struct xdg_toplevel *xdg_toplevel;
    struct wp_viewport *viewport;
    struct wl_buffer *buffer;

    int width;
    int height;
    int buf_width;
    int buf_height;
    bool configured;
    bool running;
};

static int create_shm_buffer(struct app_state *state, int w, int h) {
    int stride = w * 4;
    size_t size = (size_t)stride * (size_t)h;

    int fd = memfd_create("black-screen-shm", MFD_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    if (ftruncate(fd, (off_t)size) < 0) {
        close(fd);
        return -1;
    }

    void *data = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (data == MAP_FAILED) {
        close(fd);
        return -1;
    }

    /* XRGB8888: 0xFF000000 = opaque pure black */
    uint32_t *pixels = (uint32_t *)data;
    size_t count = (size_t)w * (size_t)h;
    for (size_t i = 0; i < count; i++) {
        pixels[i] = 0xFF000000u;
    }
    munmap(data, size);

    struct wl_shm_pool *pool = wl_shm_create_pool(state->shm, fd, (int32_t)size);
    struct wl_buffer *buf = wl_shm_pool_create_buffer(
        pool, 0, w, h, stride, WL_SHM_FORMAT_XRGB8888);
    wl_shm_pool_destroy(pool);
    close(fd);

    if (!buf) {
        return -1;
    }
    if (state->buffer) {
        wl_buffer_destroy(state->buffer);
    }
    state->buffer = buf;
    state->buf_width = w;
    state->buf_height = h;
    return 0;
}

static void commit_black_frame(struct app_state *state) {
    int target_w = state->width > 0 ? state->width : 2560;
    int target_h = state->height > 0 ? state->height : 1600;

    if (state->viewporter) {
        if (!state->buffer) {
            if (create_shm_buffer(state, 1, 1) < 0) {
                state->running = false;
                return;
            }
        }
        if (!state->viewport) {
            state->viewport = wp_viewporter_get_viewport(state->viewporter, state->surface);
        }
        wp_viewport_set_destination(state->viewport, target_w, target_h);
    } else {
        if (!state->buffer || state->buf_width != target_w || state->buf_height != target_h) {
            if (create_shm_buffer(state, target_w, target_h) < 0) {
                state->running = false;
                return;
            }
        }
    }

    wl_surface_attach(state->surface, state->buffer, 0, 0);
    wl_surface_damage_buffer(state->surface, 0, 0, INT32_MAX, INT32_MAX);
    wl_surface_commit(state->surface);
}

/* xdg_wm_base */
static void wm_base_ping(void *data, struct xdg_wm_base *wm_base, uint32_t serial) {
    (void)data;
    xdg_wm_base_pong(wm_base, serial);
}

static const struct xdg_wm_base_listener wm_base_listener = {
    .ping = wm_base_ping,
};

/* xdg_surface */
static void xdg_surface_configure(void *data, struct xdg_surface *xdg_surface, uint32_t serial) {
    struct app_state *state = (struct app_state *)data;
    xdg_surface_ack_configure(xdg_surface, serial);
    state->configured = true;
    commit_black_frame(state);
}

static const struct xdg_surface_listener xdg_surface_listener = {
    .configure = xdg_surface_configure,
};

/* xdg_toplevel */
static void xdg_toplevel_configure(void *data, struct xdg_toplevel *toplevel,
                                   int32_t width, int32_t height, struct wl_array *states) {
    (void)toplevel;
    (void)states;
    struct app_state *state = (struct app_state *)data;
    if (width > 0 && height > 0) {
        state->width = width;
        state->height = height;
    }
}

static void xdg_toplevel_close(void *data, struct xdg_toplevel *toplevel) {
    (void)toplevel;
    struct app_state *state = (struct app_state *)data;
    state->running = false;
}

static void xdg_toplevel_configure_bounds(void *data, struct xdg_toplevel *toplevel,
                                          int32_t width, int32_t height) {
    (void)data; (void)toplevel; (void)width; (void)height;
}

static void xdg_toplevel_wm_capabilities(void *data, struct xdg_toplevel *toplevel,
                                         struct wl_array *capabilities) {
    (void)data; (void)toplevel; (void)capabilities;
}

static const struct xdg_toplevel_listener xdg_toplevel_listener = {
    .configure = xdg_toplevel_configure,
    .close = xdg_toplevel_close,
    .configure_bounds = xdg_toplevel_configure_bounds,
    .wm_capabilities = xdg_toplevel_wm_capabilities,
};

/* wl_pointer: hide cursor & exit on click */
static void pointer_enter(void *data, struct wl_pointer *pointer, uint32_t serial,
                          struct wl_surface *surface, wl_fixed_t sx, wl_fixed_t sy) {
    (void)data; (void)surface; (void)sx; (void)sy;
    wl_pointer_set_cursor(pointer, serial, NULL, 0, 0);
}
static void pointer_leave(void *data, struct wl_pointer *p, uint32_t s, struct wl_surface *surf) {
    (void)data; (void)p; (void)s; (void)surf;
}
static void pointer_motion(void *data, struct wl_pointer *p, uint32_t t, wl_fixed_t sx, wl_fixed_t sy) {
    (void)data; (void)p; (void)t; (void)sx; (void)sy;
}
static void pointer_button(void *data, struct wl_pointer *p, uint32_t serial, uint32_t time,
                           uint32_t button, uint32_t state_w) {
    (void)p; (void)serial; (void)time; (void)button;
    if (state_w == WL_POINTER_BUTTON_STATE_PRESSED) {
        ((struct app_state *)data)->running = false;
    }
}
static void pointer_axis(void *data, struct wl_pointer *p, uint32_t t, uint32_t a, wl_fixed_t v) {
    (void)data; (void)p; (void)t; (void)a; (void)v;
}
static void pointer_frame(void *data, struct wl_pointer *p) { (void)data; (void)p; }
static void pointer_axis_source(void *data, struct wl_pointer *p, uint32_t s) { (void)data; (void)p; (void)s; }
static void pointer_axis_stop(void *data, struct wl_pointer *p, uint32_t t, uint32_t a) { (void)data; (void)p; (void)t; (void)a; }
static void pointer_axis_discrete(void *data, struct wl_pointer *p, uint32_t a, int32_t d) { (void)data; (void)p; (void)a; (void)d; }
static void pointer_axis_value120(void *data, struct wl_pointer *p, uint32_t a, int32_t v) { (void)data; (void)p; (void)a; (void)v; }
static void pointer_axis_relative_direction(void *data, struct wl_pointer *p, uint32_t a, uint32_t d) { (void)data; (void)p; (void)a; (void)d; }

static const struct wl_pointer_listener pointer_listener = {
    .enter = pointer_enter,
    .leave = pointer_leave,
    .motion = pointer_motion,
    .button = pointer_button,
    .axis = pointer_axis,
    .frame = pointer_frame,
    .axis_source = pointer_axis_source,
    .axis_stop = pointer_axis_stop,
    .axis_discrete = pointer_axis_discrete,
    .axis_value120 = pointer_axis_value120,
    .axis_relative_direction = pointer_axis_relative_direction,
};

/* wl_keyboard: exit on any key press */
static void keyboard_keymap(void *data, struct wl_keyboard *kb, uint32_t fmt, int32_t fd, uint32_t sz) {
    (void)data; (void)kb; (void)fmt; (void)sz;
    close(fd);
}
static void keyboard_enter(void *data, struct wl_keyboard *kb, uint32_t s, struct wl_surface *surf, struct wl_array *keys) {
    (void)data; (void)kb; (void)s; (void)surf; (void)keys;
}
static void keyboard_leave(void *data, struct wl_keyboard *kb, uint32_t s, struct wl_surface *surf) {
    (void)data; (void)kb; (void)s; (void)surf;
}
static void keyboard_key(void *data, struct wl_keyboard *kb, uint32_t serial, uint32_t time,
                         uint32_t key, uint32_t state_w) {
    (void)kb; (void)serial; (void)time; (void)key;
    if (state_w == WL_KEYBOARD_KEY_STATE_PRESSED) {
        ((struct app_state *)data)->running = false;
    }
}
static void keyboard_modifiers(void *data, struct wl_keyboard *kb, uint32_t s, uint32_t d, uint32_t l, uint32_t o, uint32_t g) {
    (void)data; (void)kb; (void)s; (void)d; (void)l; (void)o; (void)g;
}
static void keyboard_repeat_info(void *data, struct wl_keyboard *kb, int32_t r, int32_t d) {
    (void)data; (void)kb; (void)r; (void)d;
}

static const struct wl_keyboard_listener keyboard_listener = {
    .keymap = keyboard_keymap,
    .enter = keyboard_enter,
    .leave = keyboard_leave,
    .key = keyboard_key,
    .modifiers = keyboard_modifiers,
    .repeat_info = keyboard_repeat_info,
};

/* wl_touch: exit on touch down */
static void touch_down(void *data, struct wl_touch *touch, uint32_t serial, uint32_t time,
                       struct wl_surface *surface, int32_t id, wl_fixed_t x, wl_fixed_t y) {
    (void)touch; (void)serial; (void)time; (void)surface; (void)id; (void)x; (void)y;
    ((struct app_state *)data)->running = false;
}
static void touch_up(void *data, struct wl_touch *t, uint32_t s, uint32_t time, int32_t id) {
    (void)data; (void)t; (void)s; (void)time; (void)id;
}
static void touch_motion(void *data, struct wl_touch *t, uint32_t time, int32_t id, wl_fixed_t x, wl_fixed_t y) {
    (void)data; (void)t; (void)time; (void)id; (void)x; (void)y;
}
static void touch_frame(void *data, struct wl_touch *t) { (void)data; (void)t; }
static void touch_cancel(void *data, struct wl_touch *t) { (void)data; (void)t; }
static void touch_shape(void *data, struct wl_touch *t, int32_t id, wl_fixed_t maj, wl_fixed_t min) {
    (void)data; (void)t; (void)id; (void)maj; (void)min;
}
static void touch_orientation(void *data, struct wl_touch *t, int32_t id, wl_fixed_t o) {
    (void)data; (void)t; (void)id; (void)o;
}

static const struct wl_touch_listener touch_listener = {
    .down = touch_down,
    .up = touch_up,
    .motion = touch_motion,
    .frame = touch_frame,
    .cancel = touch_cancel,
    .shape = touch_shape,
    .orientation = touch_orientation,
};

/* wl_seat */
static void seat_capabilities(void *data, struct wl_seat *seat, uint32_t caps) {
    struct app_state *state = (struct app_state *)data;

    if ((caps & WL_SEAT_CAPABILITY_POINTER) && !state->pointer) {
        state->pointer = wl_seat_get_pointer(seat);
        wl_pointer_add_listener(state->pointer, &pointer_listener, state);
    } else if (!(caps & WL_SEAT_CAPABILITY_POINTER) && state->pointer) {
        wl_pointer_destroy(state->pointer);
        state->pointer = NULL;
    }

    if ((caps & WL_SEAT_CAPABILITY_KEYBOARD) && !state->keyboard) {
        state->keyboard = wl_seat_get_keyboard(seat);
        wl_keyboard_add_listener(state->keyboard, &keyboard_listener, state);
    } else if (!(caps & WL_SEAT_CAPABILITY_KEYBOARD) && state->keyboard) {
        wl_keyboard_destroy(state->keyboard);
        state->keyboard = NULL;
    }

    if ((caps & WL_SEAT_CAPABILITY_TOUCH) && !state->touch) {
        state->touch = wl_seat_get_touch(seat);
        wl_touch_add_listener(state->touch, &touch_listener, state);
    } else if (!(caps & WL_SEAT_CAPABILITY_TOUCH) && state->touch) {
        wl_touch_destroy(state->touch);
        state->touch = NULL;
    }
}

static void seat_name(void *data, struct wl_seat *seat, const char *name) {
    (void)data; (void)seat; (void)name;
}

static const struct wl_seat_listener seat_listener = {
    .capabilities = seat_capabilities,
    .name = seat_name,
};

/* wl_registry */
static void registry_global(void *data, struct wl_registry *registry, uint32_t id,
                            const char *interface, uint32_t version) {
    struct app_state *state = (struct app_state *)data;

    if (strcmp(interface, wl_compositor_interface.name) == 0) {
        uint32_t v = version < 4 ? version : 4;
        state->compositor = wl_registry_bind(registry, id, &wl_compositor_interface, v);
    } else if (strcmp(interface, wl_shm_interface.name) == 0) {
        state->shm = wl_registry_bind(registry, id, &wl_shm_interface, 1);
    } else if (strcmp(interface, xdg_wm_base_interface.name) == 0) {
        uint32_t v = version < 2 ? version : 2;
        state->wm_base = wl_registry_bind(registry, id, &xdg_wm_base_interface, v);
        xdg_wm_base_add_listener(state->wm_base, &wm_base_listener, state);
    } else if (strcmp(interface, wl_seat_interface.name) == 0) {
        uint32_t v = version < 5 ? version : 5;
        state->seat = wl_registry_bind(registry, id, &wl_seat_interface, v);
        wl_seat_add_listener(state->seat, &seat_listener, state);
    } else if (strcmp(interface, wp_viewporter_interface.name) == 0) {
        state->viewporter = wl_registry_bind(registry, id, &wp_viewporter_interface, 1);
    }
}

static void registry_global_remove(void *data, struct wl_registry *registry, uint32_t id) {
    (void)data; (void)registry; (void)id;
}

static const struct wl_registry_listener registry_listener = {
    .global = registry_global,
    .global_remove = registry_global_remove,
};

int main(void) {
    int lock_fd = open(LOCK_FILE, O_CREAT | O_RDWR, 0666);
    if (lock_fd >= 0) {
        if (flock(lock_fd, LOCK_EX | LOCK_NB) != 0) {
            close(lock_fd);
            return 0;
        }
    }

    if (!getenv("XDG_RUNTIME_DIR")) {
        setenv("XDG_RUNTIME_DIR", "/run/user/1000", 1);
    }
    if (!getenv("WAYLAND_DISPLAY")) {
        setenv("WAYLAND_DISPLAY", "wayland-0", 1);
    }

    struct app_state state;
    memset(&state, 0, sizeof(state));
    state.running = true;

    state.display = wl_display_connect(NULL);
    if (!state.display) {
        fprintf(stderr, "Failed to connect to Wayland display\n");
        return 1;
    }

    state.registry = wl_display_get_registry(state.display);
    wl_registry_add_listener(state.registry, &registry_listener, &state);
    wl_display_roundtrip(state.display);

    if (!state.compositor || !state.shm || !state.wm_base) {
        fprintf(stderr, "Missing required Wayland globals\n");
        wl_display_disconnect(state.display);
        return 1;
    }

    state.surface = wl_compositor_create_surface(state.compositor);
    state.xdg_surface = xdg_wm_base_get_xdg_surface(state.wm_base, state.surface);
    xdg_surface_add_listener(state.xdg_surface, &xdg_surface_listener, &state);

    state.xdg_toplevel = xdg_surface_get_toplevel(state.xdg_surface);
    xdg_toplevel_add_listener(state.xdg_toplevel, &xdg_toplevel_listener, &state);
    xdg_toplevel_set_title(state.xdg_toplevel, "OLED Black Screen Saver");
    xdg_toplevel_set_app_id(state.xdg_toplevel, "black-screen-saver");
    xdg_toplevel_set_fullscreen(state.xdg_toplevel, NULL);

    wl_surface_commit(state.surface);
    wl_display_roundtrip(state.display);

    while (state.running && wl_display_dispatch(state.display) != -1) {
        /* Idle blocked in poll until touch, click, key, or close */
    }

    if (state.buffer) wl_buffer_destroy(state.buffer);
    if (state.viewport) wp_viewport_destroy(state.viewport);
    if (state.xdg_toplevel) xdg_toplevel_destroy(state.xdg_toplevel);
    if (state.xdg_surface) xdg_surface_destroy(state.xdg_surface);
    if (state.surface) wl_surface_destroy(state.surface);
    if (state.touch) wl_touch_destroy(state.touch);
    if (state.keyboard) wl_keyboard_destroy(state.keyboard);
    if (state.pointer) wl_pointer_destroy(state.pointer);
    if (state.seat) wl_seat_destroy(state.seat);
    if (state.viewporter) wp_viewporter_destroy(state.viewporter);
    if (state.wm_base) xdg_wm_base_destroy(state.wm_base);
    if (state.shm) wl_shm_destroy(state.shm);
    if (state.compositor) wl_compositor_destroy(state.compositor);
    if (state.registry) wl_registry_destroy(state.registry);
    wl_display_disconnect(state.display);

    if (lock_fd >= 0) close(lock_fd);
    return 0;
}
