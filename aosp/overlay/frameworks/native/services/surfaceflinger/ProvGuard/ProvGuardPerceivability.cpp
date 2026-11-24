/*
 * Copyright (C) 2026 ProvGuard Authors
 * Licensed under the Apache License, Version 2.0.
 */
#include "ProvGuardPerceivability.h"

#include <algorithm>
#include <cmath>

namespace android::provguard {

namespace {

inline float srgbChannelToLinear(uint8_t channel) {
    const float c = static_cast<float>(channel) / 255.0f;
    return (c <= 0.04045f) ? (c / 12.92f) : std::pow((c + 0.055f) / 1.055f, 2.4f);
}

inline float relativeLuminance(uint8_t r, uint8_t g, uint8_t b) {
    return 0.2126f * srgbChannelToLinear(r)
         + 0.7152f * srgbChannelToLinear(g)
         + 0.0722f * srgbChannelToLinear(b);
}

/**
 * Estimate visible fraction after occlusion by upper layers using an adaptive 16x16 grid
 * over the node's on-screen intersection. A sample point is occluded iff the Porter-Duff
 * combined opacity 1 - prod(1 - alpha_i) of covering upper layers >= maxOccludingOpacity.
 */
float computeVisibleFraction(
        const RectI& onScreen,
        const std::vector<OccludingLayer>& upperLayers,
        float maxOccludingOpacity) {
    if (onScreen.area() <= 0) {
        return 0.0f;
    }
    if (upperLayers.empty()) {
        return 1.0f;
    }
    constexpr int kGrid = 16;
    const float dx = static_cast<float>(onScreen.right - onScreen.left) / kGrid;
    const float dy = static_cast<float>(onScreen.bottom - onScreen.top) / kGrid;
    int visibleSamples = 0;
    const int totalSamples = kGrid * kGrid;

    for (int gy = 0; gy < kGrid; ++gy) {
        const float py = onScreen.top + (gy + 0.5f) * dy;
        for (int gx = 0; gx < kGrid; ++gx) {
            const float px = onScreen.left + (gx + 0.5f) * dx;
            float transparency = 1.0f;
            for (const auto& layer : upperLayers) {
                if (px >= layer.bounds.left && px < layer.bounds.right &&
                    py >= layer.bounds.top && py < layer.bounds.bottom) {
                    const float a = std::clamp(layer.alpha, 0.0f, 1.0f);
                    transparency *= (1.0f - a);
                }
            }
            const float combinedOpacity = 1.0f - transparency;
            if (combinedOpacity < maxOccludingOpacity) {
                ++visibleSamples;
            }
        }
    }
    return static_cast<float>(visibleSamples) / static_cast<float>(totalSamples);
}

}  // namespace

float computeRegionContrastWcag(
        const RectI& region,
        const uint8_t* rgbaFrame,
        int32_t frameWidth,
        int32_t frameHeight,
        int32_t frameStrideBytes) {
    if (!rgbaFrame || frameWidth <= 0 || frameHeight <= 0 || frameStrideBytes < frameWidth * 4) {
        return 1.0f;  // Conservative fallback: cannot verify -> fails P3
    }
    RectI frameBounds{0, 0, frameWidth, frameHeight};
    RectI clipped = region.intersect(frameBounds);
    if (clipped.area() <= 0) {
        return 1.0f;
    }

    const int32_t w = clipped.right - clipped.left;
    const int32_t h = clipped.bottom - clipped.top;
    // Subsample large regions to bound SurfaceFlinger hook latency under 0.5 ms
    const int32_t stepX = std::max<int32_t>(1, w / 64);
    const int32_t stepY = std::max<int32_t>(1, h / 64);

    std::vector<float> luminances;
    luminances.reserve(((w + stepX - 1) / stepX) * ((h + stepY - 1) / stepY));
    for (int32_t y = clipped.top; y < clipped.bottom; y += stepY) {
        const uint8_t* row = rgbaFrame + static_cast<size_t>(y) * frameStrideBytes;
        for (int32_t x = clipped.left; x < clipped.right; x += stepX) {
            const uint8_t* px = row + static_cast<size_t>(x) * 4;
            luminances.push_back(relativeLuminance(px[0], px[1], px[2]));
        }
    }
    if (luminances.size() < 2) {
        return 1.0f;
    }

    // Paper calibrated 1st and 99th luminance percentiles (robust for thin text strokes)
    const size_t n = luminances.size();
    const size_t lowIdx = static_cast<size_t>(std::floor(0.01 * (n - 1)));
    const size_t highIdx = static_cast<size_t>(std::ceil(0.99 * (n - 1)));
    std::nth_element(luminances.begin(), luminances.begin() + lowIdx, luminances.end());
    const float lDark = luminances[lowIdx];
    std::nth_element(luminances.begin(), luminances.begin() + highIdx, luminances.end());
    const float lLight = luminances[highIdx];

    return (lLight + 0.05f) / (lDark + 0.05f);
}

PerceivabilityResult evaluateLayerPerceivability(
        const RectI& nodeBounds,
        const RectI& displaySafeBounds,
        float layerEffectiveAlpha,
        const std::vector<OccludingLayer>& upperLayers,
        const uint8_t* rgbaFrame,
        int32_t frameWidth,
        int32_t frameHeight,
        int32_t frameStrideBytes,
        const PerceivabilityThresholds& thresholds) {
    PerceivabilityResult res;
    res.effectiveAlpha = layerEffectiveAlpha;

    const int64_t totalArea = nodeBounds.area();
    if (totalArea <= 0) {
        // Conservative by construction: non-rendered / a11y-only nodes yield perceivable = false.
        res.perceivable = false;
        return res;
    }

    // P1: On-screen fraction outside display cutouts
    RectI onScreen = nodeBounds.intersect(displaySafeBounds);
    res.onScreenFraction =
            static_cast<float>(onScreen.area()) / static_cast<float>(totalArea);

    // P2: Visible fraction after occlusion by upper layers
    res.visibleFraction =
            computeVisibleFraction(onScreen, upperLayers, thresholds.maxOccludingOpacity);

    // P3: WCAG 2.1 contrast ratio on composed pixels
    res.contrastRatio =
            computeRegionContrastWcag(onScreen, rgbaFrame, frameWidth, frameHeight, frameStrideBytes);

    // P4: Minimum effective alpha
    const bool p1 = res.onScreenFraction >= thresholds.minOnScreenFraction;
    const bool p2 = res.visibleFraction >= thresholds.minVisibleFraction;
    const bool p3 = res.contrastRatio >= thresholds.minContrastRatio;
    const bool p4 = res.effectiveAlpha >= thresholds.minEffectiveAlpha;

    res.perceivable = p1 && p2 && p3 && p4;
    return res;
}

}  // namespace android::provguard
