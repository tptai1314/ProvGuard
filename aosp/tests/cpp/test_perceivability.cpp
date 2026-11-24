/*
 * Host-side C++20 verification test for SurfaceFlinger ProvGuardPerceivability (P1-P4).
 */
#include "ProvGuardPerceivability.h"

#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>

int main() {
    using namespace android::provguard;

    const int32_t W = 200;
    const int32_t H = 200;
    const int32_t stride = W * 4;
    const RectI display{0, 0, W, H};

    // 1. High-contrast black text on white background -> perceivable = true
    std::vector<uint8_t> highContrast(W * H * 4, 255);
    for (int y = 40; y < 80; ++y) {
        for (int x = 40; x < 60; ++x) {
            size_t idx = static_cast<size_t>(y) * stride + x * 4;
            highContrast[idx + 0] = 10;
            highContrast[idx + 1] = 10;
            highContrast[idx + 2] = 10;
        }
    }
    RectI box{20, 20, 120, 120};
    auto resVisible = evaluateLayerPerceivability(
            box, display, 1.0f, {}, highContrast.data(), W, H, stride);
    assert(resVisible.perceivable);
    assert(resVisible.contrastRatio > 10.0f);

    // 2. Low-contrast light gray on white (hidden text attack) -> perceivable = false (fails P3)
    std::vector<uint8_t> lowContrast(W * H * 4, 250);
    for (int y = 40; y < 80; ++y) {
        for (int x = 40; x < 60; ++x) {
            size_t idx = static_cast<size_t>(y) * stride + x * 4;
            lowContrast[idx + 0] = 242;
            lowContrast[idx + 1] = 242;
            lowContrast[idx + 2] = 242;
        }
    }
    auto resHidden = evaluateLayerPerceivability(
            box, display, 1.0f, {}, lowContrast.data(), W, H, stride);
    assert(!resHidden.perceivable);
    assert(resHidden.contrastRatio < 3.0f);

    // 3. Opaque upper overlay occluding node -> perceivable = false (fails P2)
    std::vector<OccludingLayer> upper{{RectI{0, 0, 200, 200}, 0.95f}};
    auto resOccluded = evaluateLayerPerceivability(
            box, display, 1.0f, upper, highContrast.data(), W, H, stride);
    assert(!resOccluded.perceivable);
    assert(resOccluded.visibleFraction == 0.0f);

    // 4. Zero-area a11y-only node -> perceivable = false
    auto resZero = evaluateLayerPerceivability(
            RectI{0, 0, 0, 0}, display, 1.0f, {}, highContrast.data(), W, H, stride);
    assert(!resZero.perceivable);

    std::cout << "ProvGuardPerceivability C++20 test: ALL CHECKS PASSED (high="
              << resVisible.contrastRatio << ", low=" << resHidden.contrastRatio << ")\n";
    return 0;
}
