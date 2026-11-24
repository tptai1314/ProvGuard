/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
#pragma once

#include <cstdint>
#include <vector>

namespace android::provguard {

struct RectI {
    int32_t left = 0;
    int32_t top = 0;
    int32_t right = 0;
    int32_t bottom = 0;

    int64_t area() const {
        if (right <= left || bottom <= top) return 0;
        return static_cast<int64_t>(right - left) * static_cast<int64_t>(bottom - top);
    }

    RectI intersect(const RectI& other) const {
        RectI r;
        r.left = left > other.left ? left : other.left;
        r.top = top > other.top ? top : other.top;
        r.right = right < other.right ? right : other.right;
        r.bottom = bottom < other.bottom ? bottom : other.bottom;
        if (r.right < r.left) r.right = r.left;
        if (r.bottom < r.top) r.bottom = r.top;
        return r;
    }
};

struct OccludingLayer {
    RectI bounds;
    float alpha = 1.0f;  // effective alpha in [0, 1]
};

struct PerceivabilityThresholds {
    float minOnScreenFraction = 0.5f;   // phi_on (Table 7)
    float minVisibleFraction = 0.5f;    // phi_vis (Table 7)
    float minContrastRatio = 3.0f;      // c_min (Table 7)
    float minEffectiveAlpha = 0.05f;    // alpha_min (Table 7)
    float maxOccludingOpacity = 0.8f;   // alpha^occ_max (Table 7)
};

struct PerceivabilityResult {
    bool perceivable = false;
    float onScreenFraction = 0.0f;
    float visibleFraction = 0.0f;
    float contrastRatio = 1.0f;
    float effectiveAlpha = 0.0f;
};

/**
 * Evaluate ProvGuard Perceivability (Paper Definition 10: P1, P2, P3, P4)
 * from SurfaceFlinger layer geometry and composed RGBA_8888 frame pixels.
 */
PerceivabilityResult evaluateLayerPerceivability(
        const RectI& nodeBounds,
        const RectI& displaySafeBounds,
        float layerEffectiveAlpha,
        const std::vector<OccludingLayer>& upperLayers,
        const uint8_t* rgbaFrame,
        int32_t frameWidth,
        int32_t frameHeight,
        int32_t frameStrideBytes,
        const PerceivabilityThresholds& thresholds = PerceivabilityThresholds{});

/** Compute WCAG 2.1 contrast ratio between 1st and 99th percentile pixel luminances. */
float computeRegionContrastWcag(
        const RectI& region,
        const uint8_t* rgbaFrame,
        int32_t frameWidth,
        int32_t frameHeight,
        int32_t frameStrideBytes);

}  // namespace android::provguard
