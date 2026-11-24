/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
#include "ProvGuardInputHook.h"

namespace android::provguard {

namespace {

inline bool containsPoint(const LiveInputWindowInfo& w, float x, float y) {
    return x >= static_cast<float>(w.left) && x < static_cast<float>(w.right)
        && y >= static_cast<float>(w.top) && y < static_cast<float>(w.bottom);
}

}  // namespace

InputBindStatus verifyDispatchTargetLocked(
        const ExpectedDispatchTarget& expected,
        const std::vector<LiveInputWindowInfo>& windowsOrderedTopToBottom) {
    if (expected.expectedToken == nullptr) {
        return InputBindStatus::ERR_TOKEN_MISSING;
    }

    const LiveInputWindowInfo* matchedWindow = nullptr;
    const LiveInputWindowInfo* topmostTouchableAtPoint = nullptr;

    for (const auto& win : windowsOrderedTopToBottom) {
        if (win.token == expected.expectedToken) {
            matchedWindow = &win;
        }
        if (expected.checkCoordinates && topmostTouchableAtPoint == nullptr
                && win.visible && win.touchable && containsPoint(win, expected.x, expected.y)) {
            topmostTouchableAtPoint = &win;
        }
    }

    if (matchedWindow == nullptr || !matchedWindow->visible) {
        return InputBindStatus::ERR_TOKEN_MISSING;
    }
    if (matchedWindow->ownerUid != expected.expectedOwnerUid) {
        return InputBindStatus::ERR_OWNER_UID_MISMATCH;
    }
    if (expected.checkCoordinates) {
        if (topmostTouchableAtPoint == nullptr
                || topmostTouchableAtPoint->token != expected.expectedToken) {
            return InputBindStatus::ERR_NOT_TOPMOST_TOUCHABLE;
        }
    }
    return InputBindStatus::OK;
}

}  // namespace android::provguard
