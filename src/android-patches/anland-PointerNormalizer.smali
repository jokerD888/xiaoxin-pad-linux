.class public final Lcom/anland/consumer/PointerNormalizer;
.super Ljava/lang/Object;

# Build an event from the pad's already observable coordinates. Changing the
# source on an existing capture event exposes its latent display rotation.
# Touchpad.recognize consumes the latest sample only, as before.
.method public static normalize(Landroid/view/MotionEvent;FFFF)Landroid/view/MotionEvent;
    .locals 18
    move-object/from16 v0, p0
    invoke-virtual {v0}, Landroid/view/MotionEvent;->getPointerCount()I
    move-result v6
    new-array v4, v6, [Landroid/view/MotionEvent$PointerCoords;
    new-array v5, v6, [Landroid/view/MotionEvent$PointerProperties;
    const/4 v1, 0x0
    :loop
    if-ge v1, v6, :ready
    new-instance v2, Landroid/view/MotionEvent$PointerCoords;
    invoke-direct {v2}, Landroid/view/MotionEvent$PointerCoords;-><init>()V
    new-instance v3, Landroid/view/MotionEvent$PointerProperties;
    invoke-direct {v3}, Landroid/view/MotionEvent$PointerProperties;-><init>()V
    invoke-virtual {v0, v1, v2}, Landroid/view/MotionEvent;->getPointerCoords(ILandroid/view/MotionEvent$PointerCoords;)V
    invoke-virtual {v0, v1, v3}, Landroid/view/MotionEvent;->getPointerProperties(ILandroid/view/MotionEvent$PointerProperties;)V
    iget v7, v2, Landroid/view/MotionEvent$PointerCoords;->x:F
    sub-float v7, v7, p3
    mul-float v7, v7, p1
    iput v7, v2, Landroid/view/MotionEvent$PointerCoords;->x:F
    iget v7, v2, Landroid/view/MotionEvent$PointerCoords;->y:F
    sub-float v7, v7, p4
    mul-float v7, v7, p2
    iput v7, v2, Landroid/view/MotionEvent$PointerCoords;->y:F
    aput-object v2, v4, v1
    aput-object v3, v5, v1
    add-int/lit8 v1, v1, 0x1
    goto :loop
    :ready
    move-object/from16 v16, p0
    move/from16 v17, v6
    move-object v7, v4
    move-object v6, v5
    invoke-virtual/range {v16 .. v16}, Landroid/view/MotionEvent;->getDownTime()J
    move-result-wide v0
    invoke-virtual/range {v16 .. v16}, Landroid/view/MotionEvent;->getEventTime()J
    move-result-wide v2
    invoke-virtual/range {v16 .. v16}, Landroid/view/MotionEvent;->getAction()I
    move-result v4
    move/from16 v5, v17
    invoke-virtual/range {v16 .. v16}, Landroid/view/MotionEvent;->getMetaState()I
    move-result v8
    invoke-virtual/range {v16 .. v16}, Landroid/view/MotionEvent;->getButtonState()I
    move-result v9
    invoke-virtual/range {v16 .. v16}, Landroid/view/MotionEvent;->getXPrecision()F
    move-result v10
    invoke-virtual/range {v16 .. v16}, Landroid/view/MotionEvent;->getYPrecision()F
    move-result v11
    invoke-virtual/range {v16 .. v16}, Landroid/view/MotionEvent;->getDeviceId()I
    move-result v12
    invoke-virtual/range {v16 .. v16}, Landroid/view/MotionEvent;->getEdgeFlags()I
    move-result v13
    const/16 v14, 0x1002
    invoke-virtual/range {v16 .. v16}, Landroid/view/MotionEvent;->getFlags()I
    move-result v15
    invoke-static/range {v0 .. v15}, Landroid/view/MotionEvent;->obtain(JJII[Landroid/view/MotionEvent$PointerProperties;[Landroid/view/MotionEvent$PointerCoords;IIFFIIII)Landroid/view/MotionEvent;
    move-result-object v0
    return-object v0
.end method
