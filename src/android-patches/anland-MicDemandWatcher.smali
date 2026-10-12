.class public final Lcom/anland/consumer/MicDemandWatcher;
.super Landroid/os/FileObserver;
.field private owner:Lcom/anland/consumer/MicDemand;

.method public constructor <init>(Ljava/lang/String;Lcom/anland/consumer/MicDemand;)V
    .locals 1
    const/16 v0, 0x3c8
    invoke-direct {p0, p1, v0}, Landroid/os/FileObserver;-><init>(Ljava/lang/String;I)V
    iput-object p2, p0, Lcom/anland/consumer/MicDemandWatcher;->owner:Lcom/anland/consumer/MicDemand;
    return-void
.end method

.method public onEvent(ILjava/lang/String;)V
    .locals 1
    const-string v0, "anland-mic-demand"
    invoke-virtual {v0, p2}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :done
    iget-object v0, p0, Lcom/anland/consumer/MicDemandWatcher;->owner:Lcom/anland/consumer/MicDemand;
    invoke-virtual {v0}, Lcom/anland/consumer/MicDemand;->changed()V
    :done
    return-void
.end method
