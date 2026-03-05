"""Tests for the multi-factor hardware tier classification system."""

from app.services.tier_classifier import (
    _score_gpu_generation,
    _score_vram,
    _score_cpu,
    _score_ram,
    _tier_from_score,
    classify_hardware_tier,
)


# ---------------------------------------------------------------------------
# GPU generation scoring
# ---------------------------------------------------------------------------


class TestScoreGpuGeneration:
    def test_none_gpu(self):
        assert _score_gpu_generation(None) == 0

    def test_empty_string(self):
        assert _score_gpu_generation("") == 0

    def test_nvidia_rtx_5090(self):
        assert _score_gpu_generation("NVIDIA GeForce RTX 5090") == 25

    def test_nvidia_rtx_4070_ti(self):
        assert _score_gpu_generation("NVIDIA GeForce RTX 4070 Ti") == 23

    def test_nvidia_rtx_3060(self):
        assert _score_gpu_generation("RTX 3060") == 20

    def test_nvidia_rtx_2080(self):
        assert _score_gpu_generation("RTX 2080") == 15

    def test_nvidia_gtx_1660(self):
        assert _score_gpu_generation("GTX 1660 Super") == 12

    def test_nvidia_gtx_1070(self):
        assert _score_gpu_generation("GTX 1070") == 10

    def test_nvidia_gtx_970(self):
        assert _score_gpu_generation("GTX 970") == 5

    def test_amd_rx_9070(self):
        assert _score_gpu_generation("AMD Radeon RX 9070 XT") == 25

    def test_amd_rx_7900_xtx(self):
        assert _score_gpu_generation("AMD Radeon RX 7900 XTX") == 23

    def test_amd_rx_6800(self):
        assert _score_gpu_generation("RX 6800 XT") == 20

    def test_amd_rx_5700(self):
        assert _score_gpu_generation("RX 5700 XT") == 15

    def test_amd_rx_580(self):
        assert _score_gpu_generation("RX 580") == 8

    def test_intel_arc_b580(self):
        assert _score_gpu_generation("Intel Arc B580") == 20

    def test_intel_arc_a770(self):
        assert _score_gpu_generation("Intel Arc A770") == 15

    def test_unknown_gpu_gets_baseline(self):
        assert _score_gpu_generation("Some Unknown GPU") == 5


# ---------------------------------------------------------------------------
# VRAM scoring
# ---------------------------------------------------------------------------


class TestScoreVram:
    def test_none(self):
        assert _score_vram(None) == 0

    def test_zero(self):
        assert _score_vram(0) == 0

    def test_24gb(self):
        assert _score_vram(24576) == 30  # 24 GB

    def test_16gb(self):
        assert _score_vram(16384) == 30  # 16 GB

    def test_12gb(self):
        assert _score_vram(12288) == 27  # 12 GB

    def test_8gb(self):
        assert _score_vram(8192) == 23   # 8 GB

    def test_6gb(self):
        assert _score_vram(6144) == 18   # 6 GB

    def test_4gb(self):
        assert _score_vram(4096) == 12   # 4 GB

    def test_2gb(self):
        assert _score_vram(2048) == 5    # 2 GB


# ---------------------------------------------------------------------------
# CPU scoring
# ---------------------------------------------------------------------------


class TestScoreCpu:
    def test_all_none(self):
        assert _score_cpu(None, None, None) == 0

    def test_16_cores(self):
        assert _score_cpu(None, 16, None) == 18

    def test_12_cores(self):
        assert _score_cpu(None, 12, None) == 15

    def test_8_cores(self):
        assert _score_cpu(None, 8, None) == 12

    def test_6_cores(self):
        assert _score_cpu(None, 6, None) == 8

    def test_4_cores(self):
        assert _score_cpu(None, 4, None) == 5

    def test_2_cores(self):
        assert _score_cpu(None, 2, None) == 2

    def test_clock_speed_bonus_5ghz(self):
        score = _score_cpu(None, 8, 5.2)
        assert score == 12 + 4  # 8 cores + 5GHz bonus

    def test_clock_speed_bonus_4_5ghz(self):
        score = _score_cpu(None, 8, 4.5)
        assert score == 12 + 3

    def test_clock_speed_bonus_4ghz(self):
        score = _score_cpu(None, 8, 4.0)
        assert score == 12 + 2

    def test_clock_speed_bonus_3_5ghz(self):
        score = _score_cpu(None, 8, 3.5)
        assert score == 12 + 1

    def test_high_perf_model_7800x3d(self):
        score = _score_cpu("AMD Ryzen 7 7800X3D", 8, 4.5)
        assert score == 12 + 3 + 3  # cores + clock + high-perf

    def test_high_perf_model_13900k(self):
        score = _score_cpu("Intel Core i9-13900K", 24, 5.8)
        assert score == 25  # capped at 25

    def test_high_perf_model_14700k(self):
        score = _score_cpu("Intel Core i7-14700K", 20, 5.5)
        assert score == 25  # 18 + 4 + 3 = 25, at cap

    def test_capped_at_25(self):
        # 16+ cores (18) + 5GHz+ (4) + high-perf (3) = 25 (capped from 25)
        score = _score_cpu("AMD Ryzen 9 9950X", 16, 5.7)
        assert score == 25


# ---------------------------------------------------------------------------
# RAM scoring
# ---------------------------------------------------------------------------


class TestScoreRam:
    def test_none(self):
        assert _score_ram(None) == 0

    def test_64gb(self):
        assert _score_ram(64) == 20

    def test_32gb(self):
        assert _score_ram(32) == 17

    def test_16gb(self):
        assert _score_ram(16) == 12

    def test_8gb(self):
        assert _score_ram(8) == 5

    def test_4gb(self):
        assert _score_ram(4) == 2


# ---------------------------------------------------------------------------
# Tier mapping
# ---------------------------------------------------------------------------


class TestTierFromScore:
    def test_ultra(self):
        assert _tier_from_score(76) == "ultra"
        assert _tier_from_score(100) == "ultra"

    def test_high(self):
        assert _tier_from_score(56) == "high"
        assert _tier_from_score(75) == "high"

    def test_mid(self):
        assert _tier_from_score(31) == "mid"
        assert _tier_from_score(55) == "mid"

    def test_low(self):
        assert _tier_from_score(0) == "low"
        assert _tier_from_score(30) == "low"


# ---------------------------------------------------------------------------
# End-to-end classification
# ---------------------------------------------------------------------------


class TestClassifyHardwareTier:
    def test_ultra_system(self):
        """RTX 4090 24GB + 9800X3D + 64GB = ultra."""
        result = classify_hardware_tier(
            gpu="NVIDIA GeForce RTX 4090",
            vram_mb=24576,
            cpu="AMD Ryzen 7 9800X3D",
            ram_gb=64,
            cpu_cores=8,
            cpu_speed_ghz=5.2,
        )
        assert result["tier"] == "ultra"
        assert result["overall_score"] == result["vram_score"] + result["gpu_gen_score"] + result["cpu_score"] + result["ram_score"]

    def test_high_system(self):
        """RTX 3060 6GB + Ryzen 5 5600X (6 cores) + 16GB = high."""
        result = classify_hardware_tier(
            gpu="NVIDIA GeForce RTX 3060",
            vram_mb=6144,
            cpu="AMD Ryzen 5 5600X",
            ram_gb=16,
            cpu_cores=6,
            cpu_speed_ghz=3.7,
        )
        assert result["tier"] == "high"

    def test_mid_system(self):
        """GTX 1660 6GB + Ryzen 5 3600 + 16GB = mid."""
        result = classify_hardware_tier(
            gpu="NVIDIA GTX 1660 Super",
            vram_mb=6144,
            cpu="AMD Ryzen 5 3600",
            ram_gb=16,
            cpu_cores=6,
            cpu_speed_ghz=3.6,
        )
        assert result["tier"] == "mid"

    def test_low_system(self):
        """GTX 960 2GB + old CPU + 8GB = low."""
        result = classify_hardware_tier(
            gpu="NVIDIA GTX 960",
            vram_mb=2048,
            ram_gb=8,
            cpu_cores=4,
        )
        assert result["tier"] == "low"

    def test_empty_system(self):
        """No specs at all = low."""
        result = classify_hardware_tier()
        assert result["tier"] == "low"
        assert result["overall_score"] == 0

    def test_result_dict_keys(self):
        result = classify_hardware_tier(gpu="RTX 4070", vram_mb=12288)
        assert set(result.keys()) == {
            "tier", "vram_score", "gpu_gen_score", "cpu_score", "ram_score", "overall_score",
        }
