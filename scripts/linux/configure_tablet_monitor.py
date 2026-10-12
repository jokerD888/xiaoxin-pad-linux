#!/usr/bin/python
"""Generate per-user overrides for Android host sensors without editing KDE packages."""
from pathlib import Path
import re

dest = Path('/home/linux/.local/share/plasma-systemmonitor')
dest.mkdir(parents=True, exist_ok=True)

def page(name):
    text = (Path('/usr/share/plasma-systemmonitor') / name).read_text()
    return re.sub(r'^\w+\[[^\n=]*\]=.*\n', '', text, flags=re.M)

def group(text, name, replacements):
    pattern = r'(^' + re.escape(name) + r'\n)(.*?)(?=^\[|\Z)'
    def replace(match):
        content = match[2]
        for key, value in replacements.items():
            line = f'{key}={value}'
            if re.search(r'^' + re.escape(key) + '=', content, re.M):
                content = re.sub(r'^' + re.escape(key) + r'=.*$', lambda _: line, content, flags=re.M)
            else:
                content = content.rstrip() + '\n' + line + '\n\n'
        return match[1] + content
    result, count = re.subn(pattern, replace, text, flags=re.M | re.S)
    if count != 1:
        raise ValueError(f'Expected one {name}, found {count}')
    return result

overview = page('overview.page')
overview = group(overview, '[page]', {'Title': '系统概览'})
overview = group(overview, '[Face-106123413726736][Appearance]', {'Title': '内存'})
overview = group(overview, '[Face-99554503711904][Appearance]', {'Title': '交换空间'})
overview = group(overview, '[Face-106123406501568][Sensors]', {
    'highPrioritySensorIds': '["tablet/gpu/usage"]', 'totalSensors': '["tablet/gpu/usage"]'})
overview = group(overview, '[Face-106123406501568][Appearance]', {'Title': 'GPU · Adreno 650'})
overview = group(overview, '[Face-106123488899456][Sensors]', {
    'highPrioritySensorIds': '["tablet/storage/used"]',
    'lowPrioritySensorIds': '["tablet/storage/free","tablet/storage/total"]'})
overview = group(overview, '[Face-106123488899456][Appearance]', {'Title': '内部存储（Android 与 Linux 共享）'})
overview = group(overview, '[Face-101427258480848][Appearance]', {
    'chartFace': 'org.kde.ksysguard.linechart', 'Title': 'Wi-Fi · wlan0（宿主总流量）'})
overview = group(overview, '[Face-101427258480848][Sensors]', {
    'highPrioritySensorIds': '["tablet/wlan0/download","tablet/wlan0/upload"]', 'totalSensors': '[]'})
overview += '\n[Face-101427258480848][org.kde.ksysguard.linechart][General]\nshowLegend=true\n\n'
overview = group(overview, '[Face-108592549200736][Appearance]', {
    'chartFace': 'org.kde.ksysguard.processtable', 'Title': 'Linux 用户进程', 'showTitle': 'true'})
process_settings = '\nshowToolBar=true\nuserFilterMode=0\nsortedColumns=name,usage,memory\ncolumnWidths=0.5,0.25,0.25\nsortColumn=memory\nsortDirection=1\n'
overview += '\n[Face-108592549200736][org.kde.ksysguard.processtable][General]' + process_settings
(dest / 'overview.page').write_text(overview)

history = page('history.page')
history = group(history, '[page]', {'Title': '历史记录'})
history = re.sub(r'^Title=Memory$', 'Title=内存', history, flags=re.M)
history = re.sub(r'^Title=Network$', 'Title=网络（宿主 Wi-Fi）', history, flags=re.M)
history = history.replace('network/all/download', 'tablet/wlan0/download').replace('network/all/upload', 'tablet/wlan0/upload')
history = re.sub(r'gpu/gpu[^"\n]+/usage', 'tablet/gpu/usage', history)
(dest / 'history.page').write_text(history)

# The full Applications view also requires desktop application cgroups, absent in this chroot.
apps = page('processes.page')
apps = group(apps, '[page]', {'Title': 'Linux 用户进程', 'icon': 'view-process-own'})
apps += '\n[Face-94051759765872][org.kde.ksysguard.processtable][General]' + process_settings.replace('showToolBar=true', 'showToolBar=false')
(dest / 'applications.page').write_text(apps)
print('Created:', ', '.join(str(dest / name) for name in ('overview.page', 'history.page', 'applications.page')))
