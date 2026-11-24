/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
#pragma once

#include <binder/IBinder.h>
#include <cstdint>
#include <vector>

namespace android::provguard {

/**
 * Snapshot of a live touchable InputWindowHandle taken while holding InputDispatcher::mLock.
 * Enables atomic target-binding verification (Paper Section 5.4 & Assumption 6).
 */
struct LiveInputWindowInfo {
    sp<IBinder> token;
    int32_t ownerUid = -1;
    int32_t left = 0;
    int32_t top = 0;
    int32_t right = 0;
    int32_t bottom = 0;
    bool touchable = false;
    bool visible = false;
};

struct ExpectedDispatchTarget {
    sp<IBinder> expectedToken;
    int32_t expectedOwnerUid = -1;
    float x = 0.0f;
    float y = 0.0f;
    bool checkCoordinates = true;
};

enum class InputBindStatus : int32_t {
    OK = 0,
    ERR_TOKEN_MISSING = 1,
    ERR_OWNER_UID_MISMATCH = 2,
    ERR_NOT_TOPMOST_TOUCHABLE = 3,
};

/**
 * Verify that the expected window still exists, has matching ownerUid, and is the topmost
 * touchable window at (x, y). MUST be invoked while holding InputDispatcher::mLock so no
 * foreground window swap can interleave before enqueueing the MotionEvent.
 *
 * @param windowsOrderedTopToBottom InputDispatcher window handles ordered front-to-back.
 */
InputBindStatus verifyDispatchTargetLocked(
        const ExpectedDispatchTarget& expected,
        const std::vector<LiveInputWindowInfo>& windowsOrderedTopToBottom);

}  // namespace android::provguard
