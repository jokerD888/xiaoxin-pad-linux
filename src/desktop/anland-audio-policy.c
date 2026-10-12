/* Process-local AAudio compatibility policy for TB-J716F's idle MMAP loop.
 * No libc/JNI helpers are used; Android resolves the existing libaaudio symbol.
 */
#include <dlfcn.h>
__attribute__((visibility("default")))
int Java_com_anland_consumer_AudioPolicy_disableMMap(void *env, void *klass) {
    (void)env; (void)klass;
    /* The ROM exports this internal API; official NDK link stubs do not.
     * Resolve at runtime instead of distributing a vendor system library. */
    void *library = dlopen("libaaudio.so", RTLD_NOW | RTLD_LOCAL);
    if (!library) return -1;
    int (*set_policy)(int) = (int (*)(int))dlsym(library, "AAudio_setMMapPolicy");
    int result = set_policy ? set_policy(1) : -1;
    dlclose(library);
    return result;
}
