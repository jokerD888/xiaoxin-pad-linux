/*
 * lenovo-kbd-bridge -- Remap Lenovo P11 Pro Touch Keyboard (17ef:610b)
 * Consumer Control Globe key (evdev 635 / HID 0x0c0390) to KEY_LEFTMETA (125)
 * so Win / Win+D / Win+V / Win+R / Win+E / Win+Tab / Win+L behave like a
 * standard external PC keyboard under Anland / KDE Plasma 6.
 *
 * Only grabs the secondary Consumer Control node (the one advertising key 635),
 * leaving the primary keyboard event node untouched. Uses inotify + poll() so
 * idle CPU usage is 0% and magnetic keyboard detach/reattach is handled cleanly.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/inotify.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define LENOVO_VENDOR  0x17ef
#define LENOVO_PRODUCT 0x610b

#define KEY_LENOVO_GLOBE      633 /* HID Consumer Usage 0x0c0390 */
#define KEY_LENOVO_MUTE       634 /* HID Consumer Usage 0x0c038f */
#define KEY_LENOVO_FULLSCREEN 635 /* HID Consumer Usage 0x0c038d */

#define BITS_PER_LONG (8 * (int)sizeof(unsigned long))
#define NBITS(x)      ((((x) - 1) / BITS_PER_LONG) + 1)
#define TEST_BIT(bit, arr) \
    (((arr)[(bit) / BITS_PER_LONG] >> ((bit) % BITS_PER_LONG)) & 1UL)

static volatile sig_atomic_t g_quit = 0;

static void on_signal(int sig)
{
    (void)sig;
    g_quit = 1;
}

static int emit_ev(int ufd, uint16_t type, uint16_t code, int32_t value)
{
    struct input_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.type = type;
    ev.code = code;
    ev.value = value;
    ssize_t n = write(ufd, &ev, sizeof(ev));
    return (n == (ssize_t)sizeof(ev)) ? 0 : -1;
}

static int create_uinput_device(void)
{
    int ufd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
    if (ufd < 0)
        return -1;

    static const int keys[] = {
        KEY_ESC,
        KEY_MUTE,
        KEY_VOLUMEDOWN,
        KEY_VOLUMEUP,
        KEY_LEFTMETA,
        KEY_COFFEE,
        KEY_BACK,
        KEY_HOMEPAGE,
        KEY_BRIGHTNESSDOWN,
        KEY_BRIGHTNESSUP,
    };

    if (ioctl(ufd, UI_SET_EVBIT, EV_KEY) < 0 ||
        ioctl(ufd, UI_SET_EVBIT, EV_SYN) < 0) {
        close(ufd);
        return -1;
    }
    for (size_t i = 0; i < sizeof(keys) / sizeof(keys[0]); i++) {
        if (ioctl(ufd, UI_SET_KEYBIT, keys[i]) < 0) {
            close(ufd);
            return -1;
        }
    }

    struct uinput_setup setup;
    memset(&setup, 0, sizeof(setup));
    snprintf(setup.name, UINPUT_MAX_NAME_SIZE, "Lenovo Keyboard Linux Bridge");
    setup.id.bustype = BUS_VIRTUAL;
    /* Distinct vendor/product so Android loads Generic.kl instead of Vendor_17ef_Product_610b.kl */
    setup.id.vendor  = 0x18d1;
    setup.id.product = 0x610b;
    setup.id.version = 1;

    if (ioctl(ufd, UI_DEV_SETUP, &setup) < 0 ||
        ioctl(ufd, UI_DEV_CREATE) < 0) {
        close(ufd);
        return -1;
    }
    return ufd;
}

static bool is_target_consumer_node(int fd)
{
    struct input_id id;
    if (ioctl(fd, EVIOCGID, &id) < 0)
        return false;
    if (id.vendor != LENOVO_VENDOR || id.product != LENOVO_PRODUCT)
        return false;

    unsigned long keybits[NBITS(KEY_MAX + 1)];
    memset(keybits, 0, sizeof(keybits));
    if (ioctl(fd, EVIOCGBIT(EV_KEY, sizeof(keybits)), keybits) < 0)
        return false;

    return TEST_BIT(KEY_LENOVO_GLOBE, keybits) != 0;
}

static int open_and_grab_target(void)
{
    DIR *dir = opendir("/dev/input");
    if (!dir)
        return -1;

    struct dirent *de;
    int target_fd = -1;
    while ((de = readdir(dir)) != NULL) {
        if (strncmp(de->d_name, "event", 5) != 0)
            continue;
        char path[PATH_MAX];
        snprintf(path, sizeof(path), "/dev/input/%s", de->d_name);
        int fd = open(path, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0)
            continue;
        if (!is_target_consumer_node(fd)) {
            close(fd);
            continue;
        }
        /* Wait briefly if any key is currently pressed before grabbing */
        unsigned long pressed[NBITS(KEY_MAX + 1)];
        for (int tries = 0; tries < 20; tries++) {
            memset(pressed, 0, sizeof(pressed));
            if (ioctl(fd, EVIOCGKEY(sizeof(pressed)), pressed) < 0)
                break;
            bool any = false;
            for (size_t i = 0; i < sizeof(pressed) / sizeof(pressed[0]); i++) {
                if (pressed[i] != 0) {
                    any = true;
                    break;
                }
            }
            if (!any)
                break;
            usleep(25000);
        }
        if (ioctl(fd, EVIOCGRAB, (void *)1) < 0) {
            close(fd);
            continue;
        }
        target_fd = fd;
        break;
    }
    closedir(dir);
    return target_fd;
}

static int remap_key(uint16_t code, uint32_t msc_scan)
{
    if (msc_scan == 0x0c0390U)
        return KEY_LEFTMETA;
    if (msc_scan == 0x0c038fU)
        return KEY_MUTE;
    if (msc_scan == 0x0c038dU)
        return -1;
    switch (code) {
    case KEY_LENOVO_GLOBE:
        return KEY_LEFTMETA;
    case KEY_LENOVO_MUTE:
        return KEY_MUTE;
    case KEY_LENOVO_FULLSCREEN:
        return -1;
    case KEY_VOLUMEDOWN:
    case KEY_VOLUMEUP:
    case KEY_BRIGHTNESSDOWN:
    case KEY_BRIGHTNESSUP:
    case KEY_COFFEE:
    case KEY_BACK:
    case KEY_HOMEPAGE:
        return (int)code;
    default:
        return -1;
    }
}

static void release_tracked_keys(int ufd, bool *held_meta)
{
    if (*held_meta) {
        emit_ev(ufd, EV_KEY, KEY_LEFTMETA, 0);
        emit_ev(ufd, EV_SYN, SYN_REPORT, 0);
        *held_meta = false;
    }
}

int main(void)
{
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);
    signal(SIGHUP, on_signal);
    signal(SIGPIPE, SIG_IGN);

    int ufd = create_uinput_device();
    if (ufd < 0) {
        fprintf(stderr, "lenovo-kbd-bridge: uinput setup failed: %s\n", strerror(errno));
        return 1;
    }

    int ifd = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
    if (ifd >= 0)
        inotify_add_watch(ifd, "/dev/input", IN_CREATE | IN_DELETE | IN_ATTRIB);

    int kfd = open_and_grab_target();
    bool held_meta = false;
    bool need_sync = false;
    uint32_t last_msc_scan = 0;

    while (!g_quit) {
        if (kfd < 0)
            kfd = open_and_grab_target();

        struct pollfd pfds[2];
        nfds_t nfds = 0;
        int k_idx = -1, i_idx = -1;
        if (kfd >= 0) {
            k_idx = (int)nfds;
            pfds[nfds++] = (struct pollfd){ .fd = kfd, .events = POLLIN };
        }
        if (ifd >= 0) {
            i_idx = (int)nfds;
            pfds[nfds++] = (struct pollfd){ .fd = ifd, .events = POLLIN };
        }

        int timeout_ms = (kfd < 0) ? 1000 : -1;
        int rc = poll(pfds, nfds, timeout_ms);
        if (rc < 0) {
            if (errno == EINTR)
                continue;
            break;
        }

        if (k_idx >= 0 && (pfds[k_idx].revents & (POLLIN | POLLERR | POLLHUP | POLLNVAL))) {
            struct input_event evs[32];
            ssize_t r;
            bool drop_dev = false;
            while ((r = read(kfd, evs, sizeof(evs))) > 0) {
                size_t count = (size_t)r / sizeof(evs[0]);
                for (size_t i = 0; i < count; i++) {
                    const struct input_event *e = &evs[i];
                    if (e->type == EV_MSC && e->code == MSC_SCAN) {
                        last_msc_scan = (uint32_t)e->value;
                    } else if (e->type == EV_KEY) {
                        int mapped = remap_key(e->code, last_msc_scan);
                        last_msc_scan = 0;
                        if (mapped > 0) {
                            if (mapped == KEY_LEFTMETA)
                                held_meta = (e->value != 0);
                            emit_ev(ufd, EV_KEY, (uint16_t)mapped, e->value);
                            need_sync = true;
                        }
                    } else if (e->type == EV_SYN && e->code == SYN_REPORT) {
                        last_msc_scan = 0;
                        if (need_sync) {
                            emit_ev(ufd, EV_SYN, SYN_REPORT, 0);
                            need_sync = false;
                        }
                    }
                }
            }
            if ((r < 0 && errno != EAGAIN && errno != EINTR) ||
                (pfds[k_idx].revents & (POLLERR | POLLHUP | POLLNVAL))) {
                drop_dev = true;
            }
            if (drop_dev) {
                ioctl(kfd, EVIOCGRAB, (void *)0);
                close(kfd);
                kfd = -1;
                need_sync = false;
                release_tracked_keys(ufd, &held_meta);
            }
        }

        if (i_idx >= 0 && (pfds[i_idx].revents & POLLIN)) {
            char buf[1024];
            while (read(ifd, buf, sizeof(buf)) > 0) {}
            if (kfd < 0) {
                usleep(100000);
                kfd = open_and_grab_target();
            }
        }
    }

    if (kfd >= 0) {
        ioctl(kfd, EVIOCGRAB, (void *)0);
        close(kfd);
    }
    release_tracked_keys(ufd, &held_meta);
    if (ifd >= 0)
        close(ifd);
    ioctl(ufd, UI_DEV_DESTROY);
    close(ufd);
    return 0;
}
