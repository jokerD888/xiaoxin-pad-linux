.class public final Lcom/anland/consumer/MicDemand;
.super Ljava/lang/Object;
.implements Ljava/lang/Runnable;

.field private static instance:Lcom/anland/consumer/MicDemand;
.field private context:Landroid/content/Context;
.field private nativeBridge:Lcom/anland/consumer/Native;
.field private handler:Landroid/os/Handler;
.field private state:I
.field private watcher:Lcom/anland/consumer/MicDemandWatcher;

.method private constructor <init>(Landroid/content/Context;)V
    .locals 2
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    invoke-virtual {p1}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;
    move-result-object v0
    iput-object v0, p0, Lcom/anland/consumer/MicDemand;->context:Landroid/content/Context;
    new-instance v0, Landroid/os/Handler;
    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;
    move-result-object v1
    invoke-direct {v0, v1}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V
    iput-object v0, p0, Lcom/anland/consumer/MicDemand;->handler:Landroid/os/Handler;
    const/4 v0, -0x1
    iput v0, p0, Lcom/anland/consumer/MicDemand;->state:I
    new-instance v0, Lcom/anland/consumer/MicDemandWatcher;
    const-string v1, "/data/local/archlinux/run"
    invoke-direct {v0, v1, p0}, Lcom/anland/consumer/MicDemandWatcher;-><init>(Ljava/lang/String;Lcom/anland/consumer/MicDemand;)V
    iput-object v0, p0, Lcom/anland/consumer/MicDemand;->watcher:Lcom/anland/consumer/MicDemandWatcher;
    invoke-virtual {v0}, Landroid/os/FileObserver;->startWatching()V
    return-void
.end method

.method public static attach(Landroid/content/Context;Lcom/anland/consumer/Native;)V
    .locals 4
    sget-object v0, Lcom/anland/consumer/MicDemand;->instance:Lcom/anland/consumer/MicDemand;
    if-nez v0, :existing
    new-instance v0, Lcom/anland/consumer/MicDemand;
    invoke-direct {v0, p0}, Lcom/anland/consumer/MicDemand;-><init>(Landroid/content/Context;)V
    sput-object v0, Lcom/anland/consumer/MicDemand;->instance:Lcom/anland/consumer/MicDemand;
    :existing
    iget-object v1, v0, Lcom/anland/consumer/MicDemand;->nativeBridge:Lcom/anland/consumer/Native;
    if-eqz v1, :set_bridge
    if-eq v1, p1, :set_bridge
    const/4 v2, 0x0
    invoke-virtual {v1, v2}, Lcom/anland/consumer/Native;->setMicEnabled(Z)V
    :set_bridge
    iput-object p1, v0, Lcom/anland/consumer/MicDemand;->nativeBridge:Lcom/anland/consumer/Native;
    const/4 v1, -0x1
    iput v1, v0, Lcom/anland/consumer/MicDemand;->state:I
    invoke-virtual {v0}, Lcom/anland/consumer/MicDemand;->run()V
    return-void
.end method

.method private tick()V
    .locals 10
    const/4 v0, 0x0
    :try_start
    iget-object v1, p0, Lcom/anland/consumer/MicDemand;->context:Landroid/content/Context;
    new-instance v3, Ljava/io/File;
    const-string v4, "/data/local/archlinux/run/anland-mic-demand"
    invoke-direct {v3, v4}, Ljava/io/File;-><init>(Ljava/lang/String;)V
    invoke-static {}, Ljava/lang/System;->currentTimeMillis()J
    move-result-wide v4
    invoke-virtual {v3}, Ljava/io/File;->lastModified()J
    move-result-wide v6
    sub-long/2addr v4, v6
    const-wide/16 v6, 0x0
    cmp-long v8, v4, v6
    if-ltz v8, :apply
    const-wide/16 v6, 0xfa0
    cmp-long v8, v4, v6
    if-gtz v8, :apply
    new-instance v2, Ljava/io/FileInputStream;
    invoke-direct {v2, v3}, Ljava/io/FileInputStream;-><init>(Ljava/io/File;)V
    invoke-virtual {v2}, Ljava/io/FileInputStream;->read()I
    move-result v3
    invoke-virtual {v2}, Ljava/io/FileInputStream;->close()V
    const/16 v4, 0x31
    if-ne v3, v4, :apply
    const-string v2, "anland_settings"
    invoke-virtual {v1, v2, v0}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
    move-result-object v2
    const-string v3, "mic_enabled"
    invoke-interface {v2, v3, v0}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z
    move-result v2
    if-eqz v2, :apply
    const-string v2, "android.permission.RECORD_AUDIO"
    invoke-virtual {v1, v2}, Landroid/content/Context;->checkSelfPermission(Ljava/lang/String;)I
    move-result v2
    if-nez v2, :apply
    const/4 v0, 0x1
    :try_end
    goto :apply
    .catch Ljava/io/IOException; {:try_start .. :try_end} :failure
    :failure
    move-exception v1
    const/4 v0, 0x0
    :apply
    iget v1, p0, Lcom/anland/consumer/MicDemand;->state:I
    if-eq v1, v0, :done
    iget-object v1, p0, Lcom/anland/consumer/MicDemand;->nativeBridge:Lcom/anland/consumer/Native;
    if-eqz v1, :done
    invoke-virtual {v1, v0}, Lcom/anland/consumer/Native;->setMicEnabled(Z)V
    iput v0, p0, Lcom/anland/consumer/MicDemand;->state:I
    :done
    return-void
.end method

.method public changed()V
    .locals 1
    iget-object v0, p0, Lcom/anland/consumer/MicDemand;->handler:Landroid/os/Handler;
    invoke-virtual {v0, p0}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V
    invoke-virtual {v0, p0}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z
    return-void
.end method

.method public run()V
    .locals 3
    iget-object v0, p0, Lcom/anland/consumer/MicDemand;->handler:Landroid/os/Handler;
    invoke-virtual {v0, p0}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V
    invoke-direct {p0}, Lcom/anland/consumer/MicDemand;->tick()V
    iget v0, p0, Lcom/anland/consumer/MicDemand;->state:I
    if-eqz v0, :done
    iget-object v0, p0, Lcom/anland/consumer/MicDemand;->handler:Landroid/os/Handler;
    const-wide/16 v1, 0xfa1
    invoke-virtual {v0, p0, v1, v2}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z
    :done
    return-void
.end method
