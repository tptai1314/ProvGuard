/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
package android.security.provguard;

import android.os.IBinder;
import android.os.Parcel;
import android.os.Parcelable;

/**
 * OS-owned provenance record attached to every served accessibility node and screenshot tile
 * (Paper Eq. 1 & Section 5.1).
 */
public final class ProvenanceRecord implements Parcelable {

    public final String observationId;
    public final String regionId;
    public final int ownerUid;
    public final IBinder windowToken;
    public final int windowType;
    public final String webOrigin;
    public final String senderPackage;
    public final boolean perceivable;
    public final float contrastRatio;
    public final float visibleFraction;
    public final int integrityLabel;
    public final String nodeDigest;

    public ProvenanceRecord(
            String observationId,
            String regionId,
            int ownerUid,
            IBinder windowToken,
            int windowType,
            String webOrigin,
            String senderPackage,
            boolean perceivable,
            float contrastRatio,
            float visibleFraction,
            int integrityLabel,
            String nodeDigest) {
        this.observationId = observationId;
        this.regionId = regionId;
        this.ownerUid = ownerUid;
        this.windowToken = windowToken;
        this.windowType = windowType;
        this.webOrigin = webOrigin;
        this.senderPackage = senderPackage;
        this.perceivable = perceivable;
        this.contrastRatio = contrastRatio;
        this.visibleFraction = visibleFraction;
        this.integrityLabel = integrityLabel;
        this.nodeDigest = nodeDigest;
    }

    private ProvenanceRecord(Parcel in) {
        this.observationId = in.readString();
        this.regionId = in.readString();
        this.ownerUid = in.readInt();
        this.windowToken = in.readStrongBinder();
        this.windowType = in.readInt();
        this.webOrigin = in.readString();
        this.senderPackage = in.readString();
        this.perceivable = in.readInt() != 0;
        this.contrastRatio = in.readFloat();
        this.visibleFraction = in.readFloat();
        this.integrityLabel = in.readInt();
        this.nodeDigest = in.readString();
    }

    @Override
    public void writeToParcel(Parcel dest, int flags) {
        dest.writeString(observationId);
        dest.writeString(regionId);
        dest.writeInt(ownerUid);
        dest.writeStrongBinder(windowToken);
        dest.writeInt(windowType);
        dest.writeString(webOrigin);
        dest.writeString(senderPackage);
        dest.writeInt(perceivable ? 1 : 0);
        dest.writeFloat(contrastRatio);
        dest.writeFloat(visibleFraction);
        dest.writeInt(integrityLabel);
        dest.writeString(nodeDigest);
    }

    @Override
    public int describeContents() {
        return 0;
    }

    public static final Creator<ProvenanceRecord> CREATOR =
            new Creator<ProvenanceRecord>() {
                @Override
                public ProvenanceRecord createFromParcel(Parcel in) {
                    return new ProvenanceRecord(in);
                }

                @Override
                public ProvenanceRecord[] newArray(int size) {
                    return new ProvenanceRecord[size];
                }
            };
}
