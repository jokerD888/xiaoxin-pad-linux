#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* Magisk's PTY proxy can miss SIGWINCH while Android updates the outer PTY.
 * Keep util-linux script's Linux PTY in sync without a shell polling pipeline. */
static volatile sig_atomic_t child_pid;
static void forward_signal(int sig) {
    if (child_pid > 0) kill((pid_t)child_pid, sig);
}
static void wake_on_child(int sig) { (void)sig; }

int main(void) {
    struct winsize previous = {0};
    struct sigaction action = {0};
    if (!isatty(STDIN_FILENO)) {
        fputs("Arch terminal requires an interactive terminal.\n", stderr);
        return 1;
    }
    action.sa_handler = forward_signal;
    sigemptyset(&action.sa_mask);
    sigaction(SIGHUP, &action, NULL);
    sigaction(SIGTERM, &action, NULL);
    sigaction(SIGQUIT, &action, NULL);
    sigaction(SIGWINCH, &action, NULL);
    action.sa_handler = wake_on_child;
    sigaction(SIGCHLD, &action, NULL);
    pid_t child = fork();
    if (child < 0) { perror("fork"); return 1; }
    if (child == 0) {
        signal(SIGHUP, SIG_DFL); signal(SIGTERM, SIG_DFL);
        signal(SIGQUIT, SIG_DFL); signal(SIGWINCH, SIG_DFL);
        signal(SIGCHLD, SIG_DFL);
        execl("/usr/bin/script", "script", "--quiet", "--flush", "--return",
              "--command", "/usr/local/bin/arch-terminal --resume", "/dev/null", (char *)NULL);
        perror("script"); _exit(127);
    }
    child_pid = child;
    for (;;) {
        int status;
        pid_t finished = waitpid(child, &status, WNOHANG);
        if (finished == child)
            return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
        if (finished < 0 && errno != EINTR) { perror("waitpid"); return 1; }
        struct winsize current;
        if (ioctl(STDIN_FILENO, TIOCGWINSZ, &current) == 0 &&
            current.ws_row && current.ws_col &&
            (current.ws_row != previous.ws_row || current.ws_col != previous.ws_col)) {
            previous = current;
            kill(child, SIGWINCH);
        }
        const struct timespec interval = {1, 0};
        nanosleep(&interval, NULL);
    }
}
