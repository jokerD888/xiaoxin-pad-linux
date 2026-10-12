// SPDX-License-Identifier: MIT
// Android host metrics for KDE System Monitor inside the TB-J716F chroot.
#include <KPluginFactory>
#include <QElapsedTimer>
#include <QFile>
#include <QRegularExpression>
#include <QTextStream>
#include <systemstats/SensorPlugin.h>
#include <systemstats/SensorContainer.h>
#include <systemstats/SensorObject.h>
#include <systemstats/SensorProperty.h>
#include <sys/statvfs.h>
#include <algorithm>

using namespace KSysGuard;

class TabletSensors : public SensorPlugin {
    Q_OBJECT
public:
    TabletSensors(QObject *parent, const QVariantList &args) : SensorPlugin(parent, args) {
        auto group = new SensorContainer("tablet", QStringLiteral("平板宿主硬件"), this);
        auto gpu = new SensorObject("gpu", "Adreno 650 (KGSL)", group);
        gpuUsage = property(gpu, "usage", QStringLiteral("GPU 使用率"), UnitPercent);
        gpuUsage->setMax(100);
        gpuUsage->setDescription(QStringLiteral("Android KGSL GPU 忙碌时间 / 采样时间，宿主与 Linux 共享 GPU"));
        gpuFrequency = property(gpu, "frequency", QStringLiteral("GPU 频率"), UnitHertz);
        auto disk = new SensorObject("storage", QStringLiteral("内部存储（共享 /data）"), group);
        diskTotal = property(disk, "total", QStringLiteral("总容量"), UnitByte);
        diskUsed = property(disk, "used", QStringLiteral("已用空间"), UnitByte);
        diskFree = property(disk, "free", QStringLiteral("可用空间"), UnitByte);
        diskUsed->setMax(diskTotal);
        diskFree->setMax(diskTotal);
        auto network = new SensorObject("wlan0", "Wi-Fi (wlan0)", group);
        download = property(network, "download", QStringLiteral("Wi-Fi 下载"), UnitByteRate);
        upload = property(network, "upload", QStringLiteral("Wi-Fi 上传"), UnitByteRate);
        download->setDescription(QStringLiteral("宿主 wlan0 接口接收字节差值 / 实际采样间隔"));
        upload->setDescription(QStringLiteral("宿主 wlan0 接口发送字节差值 / 实际采样间隔"));
        clock.start();
        update();
    }
    QString providerName() const override { return "tablet_android"; }
    void update() override {
        QFile busy("/sys/class/kgsl/kgsl-3d0/gpubusy");
        if (busy.open(QIODevice::ReadOnly)) {
            QTextStream stream(&busy);
            quint64 active = 0, total = 0;
            stream >> active >> total;
            if (stream.status() == QTextStream::Ok && total > 0)
                gpuUsage->setValue(std::clamp(100.0 * double(active) / double(total), 0.0, 100.0));
            else
                gpuUsage->setValue(QVariant{});
        } else gpuUsage->setValue(QVariant{});
        QFile frequency("/sys/class/kgsl/kgsl-3d0/gpuclk");
        if (frequency.open(QIODevice::ReadOnly)) {
            bool ok = false;
            auto hz = frequency.readAll().trimmed().toULongLong(&ok);
            gpuFrequency->setValue(ok ? QVariant(double(hz)) : QVariant{});
        } else gpuFrequency->setValue(QVariant{});
        struct statvfs disk{};
        if (statvfs("/", &disk) == 0) {
            const double total = double(disk.f_blocks) * disk.f_frsize;
            diskTotal->setValue(total);
            diskUsed->setValue(double(disk.f_blocks - disk.f_bfree) * disk.f_frsize);
            diskFree->setValue(double(disk.f_bavail) * disk.f_frsize);
        } else {
            diskTotal->setValue(QVariant{}); diskUsed->setValue(QVariant{}); diskFree->setValue(QVariant{});
        }
        QFile net("/proc/net/dev");
        bool found = false;
        if (net.open(QIODevice::ReadOnly)) {
            // procfs files report zero size; readAll before splitting rather than QFile::atEnd.
            const auto lines = QString::fromLatin1(net.readAll()).split('\n');
            for (const auto &line : lines) {
                const int colon = line.indexOf(':');
                if (colon < 0 || line.left(colon).trimmed() != "wlan0") continue;
                const auto fields = line.mid(colon + 1).simplified().split(' ');
                if (fields.size() < 16) break;
                bool rxOk = false, txOk = false;
                const auto rx = fields[0].toULongLong(&rxOk);
                const auto tx = fields[8].toULongLong(&txOk);
                if (!rxOk || !txOk) break;
                const qint64 now = clock.nsecsElapsed();
                if (haveNetSample && now > lastNetTime && rx >= lastRx && tx >= lastTx) {
                    const double seconds = double(now - lastNetTime) / 1e9;
                    download->setValue(double(rx - lastRx) / seconds);
                    upload->setValue(double(tx - lastTx) / seconds);
                } else {
                    download->setValue(QVariant{}); upload->setValue(QVariant{});
                }
                lastRx = rx; lastTx = tx; lastNetTime = now; haveNetSample = true;
                found = true;
                break;
            }
        }
        if (!found) {
            haveNetSample = false;
            download->setValue(QVariant{}); upload->setValue(QVariant{});
        }
    }
private:
    static SensorProperty *property(SensorObject *obj, const QString &id, const QString &name, Unit unit) {
        auto p = new SensorProperty(id, name, obj);
        p->setShortName(name);
        p->setVariantType(QVariant::Double);
        p->setUnit(unit);
        p->setMin(0);
        return p;
    }
    SensorProperty *gpuUsage, *gpuFrequency, *diskTotal, *diskUsed, *diskFree, *download, *upload;
    QElapsedTimer clock;
    quint64 lastRx = 0, lastTx = 0;
    qint64 lastNetTime = 0;
    bool haveNetSample = false;
};

K_PLUGIN_CLASS_WITH_JSON(TabletSensors, "tablet-systemstats.json")
#include "tablet-systemstats.moc"
