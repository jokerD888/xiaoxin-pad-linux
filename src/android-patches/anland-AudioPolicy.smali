.class public final Lcom/anland/consumer/AudioPolicy;
.super Ljava/lang/Object;

.method static constructor <clinit>()V
    .locals 1
    const-string v0, "anland_audiopolicy"
    invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V
    return-void
.end method

.method public static native disableMMap()I
.end method
