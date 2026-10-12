"""Reproducible Anland patch: event-based idle frame wait plus desktop/audio fixes."""
from pathlib import Path
import re
import shutil

base = Path('.build/apk/decoded')
main = base / 'smali/com/anland/consumer/MainActivity.smali'
text = main.read_text()
text, count = re.subn(r'\.method private applyMicState\(\)V.*?\.end method', '''.method private applyMicState()V
    .locals 1
    iget-object v0, p0, Lcom/anland/consumer/MainActivity;->mNative:Lcom/anland/consumer/Native;
    invoke-static {p0, v0}, Lcom/anland/consumer/MicDemand;->attach(Landroid/content/Context;Lcom/anland/consumer/Native;)V
    return-void
.end method''', text, flags=re.S)
assert count == 1
# The keyboard has a second non-alphabetic function-key device. Accept either
# keyboard type, but continue excluding virtual navigation and mouse buttons.
text, count = re.subn(r'(\.method private isKeyboardBackKey\(Landroid/view/KeyEvent;\)Z.*?getKeyboardType\(\)I\s+move-result p0\s+)const/4 p1, 0x2\s+if-ne p0, p1, :cond_1', r'\1if-eqz p0, :cond_1', text, flags=re.S)
assert count == 1
needle = '.method private handleSourceAwareKey(Landroid/view/KeyEvent;)Z\n    .locals '
start = text.index(needle)
end = text.index('\n', start + len(needle))
insert = '''
    invoke-virtual {p1}, Landroid/view/KeyEvent;->getKeyCode()I
    move-result v0
    const/4 v1, 0x4
    if-ne v0, v1, :local_normal_key
    invoke-direct {p0, p1}, Lcom/anland/consumer/MainActivity;->isMouseKeyEvent(Landroid/view/KeyEvent;)Z
    move-result v0
    if-nez v0, :local_normal_key
    invoke-direct {p0, p1}, Lcom/anland/consumer/MainActivity;->isKeyboardBackKey(Landroid/view/KeyEvent;)Z
    move-result v0
    if-eqz v0, :local_normal_key
    const/4 v0, 0x1
    invoke-direct {p0, p1, v0}, Lcom/anland/consumer/MainActivity;->forwardKeyToLinux(Landroid/view/KeyEvent;Z)Z
    move-result v0
    return v0
    :local_normal_key
'''
locals_count = int(text[start + len(needle):end].strip())
text = text[:start+len(needle)] + str(max(2, locals_count)) + text[end:end+1] + insert + text[end+1:]
# Permission grant callback must also pass through the demand gate.
text, count = re.subn(r'iget-object p0, p0, Lcom/anland/consumer/MainActivity;->mNative:Lcom/anland/consumer/Native;\s+invoke-virtual \{p0, v0\}, Lcom/anland/consumer/Native;->setMicEnabled\(Z\)V',
                     'invoke-direct {p0}, Lcom/anland/consumer/MainActivity;->applyMicState()V', text)
assert count == 1
main.write_text(text)
shutil.copyfile('src/android-patches/anland-MicDemand.smali', base / 'smali/com/anland/consumer/MicDemand.smali')
shutil.copyfile('src/android-patches/anland-MicDemandWatcher.smali', base / 'smali/com/anland/consumer/MicDemandWatcher.smali')
shutil.copyfile('src/android-patches/anland-AudioPolicy.smali', base / 'smali/com/anland/consumer/AudioPolicy.smali')
native = base / 'smali/com/anland/consumer/Native.smali'
native_text = native.read_text()
needle = '    invoke-static {}, Lcom/anland/consumer/Native;->nativeCreate()J'
assert native_text.count(needle) == 1
native.write_text(native_text.replace(needle, '    invoke-static {}, Lcom/anland/consumer/AudioPolicy;->disableMMap()I\n\n' + needle))
shutil.copyfile('.build/libanland_audiopolicy.so', base / 'lib/arm64-v8a/libanland_audiopolicy.so')
shutil.copyfile('.build/libanland_consumer.so', base / 'lib/arm64-v8a/libanland_consumer.so')
# SOURCE_TOUCHPAD ignores the display transform. Changing an existing event to
# SOURCE_TOUCHSCREEN makes that latent landscape transform observable, rotating
# the pad by 90 degrees. Rebuild from observed coordinates, with identity display
# transform, before scaling. Keep all callers and scroll-axis semantics intact.
pad = base / 'smali/com/anland/consumer/Touchpad.smali'
pad_text = pad.read_text()
pad_text, count = re.subn(r'\.method private normalizeToOutput\(Landroid/view/MotionEvent;\)Landroid/view/MotionEvent;.*?\.end method', '''.method private normalizeToOutput(Landroid/view/MotionEvent;)Landroid/view/MotionEvent;
    .locals 5
    iget v0, p0, Lcom/anland/consumer/Touchpad;->inputRangeX:F
    iget v1, p0, Lcom/anland/consumer/Touchpad;->inputRangeY:F
    const/4 v2, 0x0
    cmpg-float v3, v0, v2
    if-lez v3, :unchanged
    cmpg-float v3, v1, v2
    if-lez v3, :unchanged
    iget v3, p0, Lcom/anland/consumer/Touchpad;->outputWidth:I
    if-lez v3, :unchanged
    int-to-float v3, v3
    div-float/2addr v3, v0
    iget v4, p0, Lcom/anland/consumer/Touchpad;->outputHeight:I
    if-lez v4, :unchanged
    int-to-float v4, v4
    div-float/2addr v4, v1
    move-object v0, p1
    move v1, v3
    move v2, v4
    iget v3, p0, Lcom/anland/consumer/Touchpad;->inputMinX:F
    iget v4, p0, Lcom/anland/consumer/Touchpad;->inputMinY:F
    invoke-static/range {v0 .. v4}, Lcom/anland/consumer/PointerNormalizer;->normalize(Landroid/view/MotionEvent;FFFF)Landroid/view/MotionEvent;
    move-result-object v0
    return-object v0
    :unchanged
    const/4 v0, 0x0
    return-object v0
.end method''', pad_text, flags=re.S)
assert count == 1
pad.write_text(pad_text)
shutil.copyfile('src/android-patches/anland-PointerNormalizer.smali', base / 'smali/com/anland/consumer/PointerNormalizer.smali')
manifest = base / 'AndroidManifest.xml'
text = manifest.read_text().replace('package="com.anland.consumer"', 'package="com.anland.consumer.desktop"')
text = text.replace('android:label="Anland"', 'android:label="Anland Linux"')
manifest.write_text(text)
key = base / 'smali/com/anland/consumer/KeyInterceptor.smali'
text = key.read_text().replace('com.anland.consumer/.KeyInterceptor', 'com.anland.consumer.desktop/com.anland.consumer.KeyInterceptor')
key.write_text(text)
shortcuts = base / 'res/xml/shortcuts.xml'
shortcuts.write_text(shortcuts.read_text().replace('android:targetPackage="com.anland.consumer"',
                                                 'android:targetPackage="com.anland.consumer.desktop"'))
metadata = base / 'apktool.yml'
metadata.write_text(re.sub(r'(versionName:).*', r'\1 5.22-367a523-desktopfix5', metadata.read_text()))
print('patched separate package; original APK and its data retained')
