#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <X11/Xutil.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/file.h>
#include <glob.h>

#define LOCK_FILE "/run/user/1000/black-screen-saver.lock"

int main() {
    int lock_fd = open(LOCK_FILE, O_CREAT | O_RDWR, 0666);
    if (lock_fd >= 0) {
        if (flock(lock_fd, LOCK_EX | LOCK_NB) != 0) {
            // Already running
            return 0;
        }
    }

    // Auto discover xauthority if not set
    if (!getenv("XAUTHORITY")) {
        glob_t glob_res;
        if (glob("/run/user/1000/xauth*", GLOB_NOSORT, NULL, &glob_res) == 0 && glob_res.gl_pathc > 0) {
            setenv("XAUTHORITY", glob_res.gl_pathv[0], 1);
        }
        globfree(&glob_res);
    }
    if (!getenv("DISPLAY")) {
        setenv("DISPLAY", ":0", 1);
    }

    Display *dpy = XOpenDisplay(NULL);
    if (!dpy) {
        dpy = XOpenDisplay(":0");
    }
    if (!dpy) {
        fprintf(stderr, "Cannot open display\n");
        return 1;
    }

    int screen = DefaultScreen(dpy);
    int width = DisplayWidth(dpy, screen);
    int height = DisplayHeight(dpy, screen);

    XSetWindowAttributes attrs;
    attrs.override_redirect = True;
    attrs.background_pixel = BlackPixel(dpy, screen);
    attrs.event_mask = KeyPressMask | ButtonPressMask | ExposureMask;

    Window win = XCreateWindow(dpy, RootWindow(dpy, screen),
                               0, 0, width, height, 0,
                               DefaultDepth(dpy, screen),
                               InputOutput,
                               DefaultVisual(dpy, screen),
                               CWOverrideRedirect | CWBackPixel | CWEventMask,
                               &attrs);

    // Hide cursor
    Pixmap blank;
    XColor dummy;
    char data[1] = {0};
    blank = XCreateBitmapFromData(dpy, win, data, 1, 1);
    Cursor cursor = XCreatePixmapCursor(dpy, blank, blank, &dummy, &dummy, 0, 0);
    XDefineCursor(dpy, win, cursor);

    // Fullscreen properties
    Atom wm_state = XInternAtom(dpy, "_NET_WM_STATE", False);
    Atom fullscreen = XInternAtom(dpy, "_NET_WM_STATE_FULLSCREEN", False);
    Atom stay_on_top = XInternAtom(dpy, "_NET_WM_STATE_STAYS_ON_TOP", False);
    Atom above = XInternAtom(dpy, "_NET_WM_STATE_ABOVE", False);
    Atom states[3] = { fullscreen, stay_on_top, above };
    XChangeProperty(dpy, win, wm_state, XA_ATOM, 32, PropModeReplace, (unsigned char *)states, 3);

    XMapRaised(dpy, win);
    XFlush(dpy);

    // Event loop: exit on any touch, click or key
    XEvent ev;
    while (1) {
        XNextEvent(dpy, &ev);
        if (ev.type == KeyPress || ev.type == ButtonPress) {
            break;
        }
    }

    XDestroyWindow(dpy, win);
    XFreeCursor(dpy, cursor);
    XFreePixmap(dpy, blank);
    XCloseDisplay(dpy);
    return 0;
}
