/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package android.security.provguard;

import android.os.IBinder;
import android.os.Parcel;
import android.os.Parcelable;

/**
 * Cryptographic and identity binding recorded for every interactive node at observation time
 * (Paper Section 5.4: bind = (tok, nid, dig, uid)).
 */
public final class TargetBinding implements Parcelable {

    public final String observationId;
    public final IBinder windowToken;
    public final long nodeId;
    public final String nodeDigest;
    public final int ownerUid;
    public final int boundsLeft;
    public final int boundsTop;
    public final int boundsRight;
    public final int boundsBottom;

    public TargetBinding(
            String observationId,
            IBinder windowToken,
            long nodeId,
            String nodeDigest,
            int ownerUid,
            int boundsLeft,
            int boundsTop,
            int boundsRight,
            int boundsBottom) {
        this.observationId = observationId;
        this.windowToken = windowToken;
        this.nodeId = nodeId;
        this.nodeDigest = nodeDigest;
        this.ownerUid = ownerUid;
        this.boundsLeft = boundsLeft;
        this.boundsTop = boundsTop;
        this.boundsRight = boundsRight;
        this.boundsBottom = boundsBottom;
    }

    private TargetBinding(Parcel in) {
        this.observationId = in.readString();
        this.windowToken = in.readStrongBinder();
        this.nodeId = in.readLong();
        this.nodeDigest = in.readString();
        this.ownerUid = in.readInt();
        this.boundsLeft = in.readInt();
        this.boundsTop = in.readInt();
        this.boundsRight = in.readInt();
        this.boundsBottom = in.readInt();
    }

    public float centerX() {
        return (boundsLeft + boundsRight) / 2.0f;
    }

    public float centerY() {
        return (boundsTop + boundsBottom) / 2.0f;
    }

    @Override
    public void writeToParcel(Parcel dest, int flags) {
        dest.writeString(observationId);
        dest.writeStrongBinder(windowToken);
        dest.writeLong(nodeId);
        dest.writeString(nodeDigest);
        dest.writeInt(ownerUid);
        dest.writeInt(boundsLeft);
        dest.writeInt(boundsTop);
        dest.writeInt(boundsRight);
        dest.writeInt(boundsBottom);
    }

    @Override
    public int describeContents() {
        return 0;
    }

    public static final Creator<TargetBinding> CREATOR =
            new Creator<TargetBinding>() {
                @Override
                public TargetBinding createFromParcel(Parcel in) {
                    return new TargetBinding(in);
                }

                @Override
                public TargetBinding[] newArray(int size) {
                    return new TargetBinding[size];
                }
            };
}
