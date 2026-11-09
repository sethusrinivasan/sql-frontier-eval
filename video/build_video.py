#!/usr/bin/env python3
"""
SQL-Frontier-Eval: Video Walkthrough Generator
Generates a full 1080p MP4 presentation video with voice narration,
synchronized closed-caption subtitles, and slide visuals.
"""

import os
import re
import subprocess
import json
from pathlib import Path
from gtts import gTTS

VIDEO_DIR = Path("/home/home/github/sql-frontier-eval/video")
SCENES_DIR = VIDEO_DIR / "scenes"
OUTPUT_DIR = Path("/home/home/github/sql-frontier-eval")
FFMPEG_BIN = "/home/home/github/sql-frontier-eval/.venv/lib/python3.14/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2"

SCENES = [
    {
        "id": 1,
        "image": SCENES_DIR / "slide_1.png",
        "subtitles": [
            ("When deploying generative AI into modern columnar data warehouses,", 3.5),
            ("the most dangerous bugs aren't syntax errors.", 2.8),
            ("It is when a query executes without a single warning,", 3.0),
            ("but silently quadruples your financial KPIs or corrupts user cohorts.", 4.2),
            ("Traditional benchmarks only test basic relational lookups and textbook joins.", 4.5),
            ("We built SQL Frontier Eval to evaluate frontier models on real-world analytical invariants.", 5.2),
        ]
    },
    {
        "id": 2,
        "image": SCENES_DIR / "slide_2.png",
        "subtitles": [
            ("To truly stress-test frontier models, we curated an eight-category failure taxonomy.", 4.8),
            ("This covers high-stakes real-world pitfalls like the Chasm Trap,", 3.8),
            ("where joining two one-to-many child tables multiplies gross revenue four-fold.", 4.5),
            ("We test Gaps and Islands sessionization with thirty-minute inactivity thresholds,", 4.5),
            ("point-in-time SCD Type Two joins with open-ended null bounds,", 4.0),
            ("and subtle three-valued logic where a single NULL in a subquery empties an entire dataset.", 5.5),
            ("We also evaluate window frame bounds, funnel precedence, and non-SARGable date pruning.", 5.2),
        ]
    },
    {
        "id": 3,
        "image": SCENES_DIR / "slide_3.png",
        "subtitles": [
            ("Under the hood, SQL Frontier Eval executes inside an isolated in-memory DuckDB sandbox.", 5.0),
            ("To eliminate test flakiness, our grader enforces deterministic multiset row sorting.", 4.5),
            ("Crucially, our engine inspects DuckDB's physical EXPLAIN plan", 3.8),
            ("to flag disallowed anti-patterns like Cartesian cross products and quadratic joins.", 4.8),
            ("And whenever an evaluation fails, the harness automatically generates a full walkthrough", 5.0),
            ("displaying side-by-side output tables, arithmetic deltas, and root-cause explanations.", 5.2),
        ]
    },
    {
        "id": 4,
        "image": SCENES_DIR / "slide_4.png",
        "subtitles": [
            ("We evaluated frontier models across major AI providers: Gemini, Claude, and GPT.", 5.0),
            ("The empirical scorecard revealed significant capability differences.", 3.8),
            ("Gemini 3.8 Flash with Medium Reasoning achieved a perfect eight out of eight,", 4.5),
            ("flawlessly handling every analytical trap.", 2.5),
            ("Claude Opus 4.6 Thinking, Claude Sonnet 4.6, GPT-OSS 120B, and Gemini Low", 4.8),
            ("all delivered fast inference and scored seven out of eight,", 3.8),
            ("with all of them failing on Task 06: strict sequential funnel precedence.", 4.8),
        ]
    },
    {
        "id": 5,
        "image": SCENES_DIR / "slide_5.png",
        "subtitles": [
            ("Here is why Task 06 was the great discriminator between frontier models.", 4.2),
            ("When calculating sequential user onboarding conversion stages,", 3.8),
            ("Claude and GPT wrote multiple unnested distinct count subqueries.", 4.2),
            ("This triggered internal Cartesian cross-product execution plans in DuckDB.", 4.5),
            ("In contrast, Gemini 3.8 Flash with Medium Reasoning synthesized a single-scan CTE", 5.0),
            ("using conditional aggregation flags that executed in just four milliseconds.", 4.2),
        ]
    },
    {
        "id": 6,
        "image": SCENES_DIR / "slide_6.png",
        "subtitles": [
            ("SQL Frontier Eval is fully reproducible and packaged for hackathon submission.", 4.5),
            ("The entire codebase is compressed into an eighty-seven kilobyte code-only archive.", 4.8),
            ("A single script, verify dot s h, executes all twelve unit tests and baselines in five seconds.", 5.2),
            ("All empirical run logs are openly committed to the Git repository.", 4.0),
            ("This evaluation suite was developed using Google Antigravity with human engineering oversight.", 5.5),
            ("Thank you, and let us make AI data engineering reliable and mathematically sound.", 4.8),
        ]
    }
]

def format_srt_time(seconds: float) -> str:
    millis = int((seconds % 1) * 1000)
    total_seconds = int(seconds)
    secs = total_seconds % 60
    mins = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def get_audio_duration(file_path: Path) -> float:
    cmd = [
        FFMPEG_BIN,
        "-i", str(file_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        h, m, s = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0

def main():
    print("=" * 70)
    print("SQL FRONTIER EVAL: VIDEO WALKTHROUGH COMPOSER")
    print("=" * 70)

    clips = []
    srt_entries = []
    srt_counter = 1
    global_time = 0.5  # 0.5s initial lead-in

    for scene in SCENES:
        scene_id = scene["id"]
        img_path = scene["image"]
        subtitles = scene["subtitles"]
        print(f"\n[Scene {scene_id}] Synthesizing speech and generating timing...")

        # Build full text for scene
        full_text = " ".join([text for text, _ in subtitles])
        audio_mp3 = VIDEO_DIR / f"scene_{scene_id}_audio.mp3"

        tts = gTTS(text=full_text, lang="en", tld="com", slow=False)
        tts.save(str(audio_mp3))

        actual_duration = get_audio_duration(audio_mp3)
        print(f"  Audio generated: {actual_duration:.2f}s across {len(subtitles)} phrases")

        # Distribute timing proportionally based on estimated durations
        sum_est = sum([est for _, est in subtitles])
        scale_factor = actual_duration / sum_est if sum_est > 0 else 1.0

        current_scene_time = 0.3  # small scene pre-padding
        for text, est in subtitles:
            dur = est * scale_factor
            start_s = global_time + current_scene_time
            end_s = start_s + dur

            srt_entries.append(
                f"{srt_counter}\n"
                f"{format_srt_time(start_s)} --> {format_srt_time(end_s)}\n"
                f"{text}\n"
            )
            srt_counter += 1
            current_scene_time += dur

        scene_total_dur = actual_duration + 0.8  # padding before/after
        global_time += scene_total_dur

        # Render individual scene video clip with padded audio
        scene_clip = VIDEO_DIR / f"scene_{scene_id}.mp4"
        print(f"  Rendering 1080p clip: {scene_clip.name} (Duration: {scene_total_dur:.2f}s)...")

        # ffmpeg command to create scene clip: loop image, add silent audio padding, encode to h264/aac
        clip_cmd = [
            FFMPEG_BIN,
            "-y",
            "-loop", "1",
            "-framerate", "25",
            "-t", f"{scene_total_dur:.2f}",
            "-i", str(img_path),
            "-i", str(audio_mp3),
            "-filter_complex",
            f"[1:a]adelay=300|300,apad=pad_dur=0.5[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(scene_clip)
        ]
        subprocess.run(clip_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        clips.append(scene_clip)

    # Write Master SRT File
    srt_file = VIDEO_DIR / "walkthrough_captions.srt"
    srt_content = "\n".join(srt_entries)
    srt_file.write_text(srt_content)
    print(f"\n[Subtitles Generated] Written to {srt_file} ({len(srt_entries)} cues)")

    # Concatenate all clips using ffmpeg concat demuxer
    concat_list = VIDEO_DIR / "concat_list.txt"
    with open(concat_list, "w") as f:
        for clip in clips:
            f.write(f"file '{clip.absolute()}'\n")

    unsubbed_video = VIDEO_DIR / "walkthrough_unsubbed.mp4"
    print(f"\n[Stitching Clips] Merging {len(clips)} scenes into {unsubbed_video.name}...")
    concat_cmd = [
        FFMPEG_BIN,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(unsubbed_video)
    ]
    subprocess.run(concat_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Burn-in high contrast closed captions
    final_output = OUTPUT_DIR / "sql_frontier_eval_walkthrough.mp4"
    print(f"\n[Burning Closed Captions] Rendering final video to {final_output.name}...")
    
    # Subtitle style: high-contrast semi-transparent box, white bold text, centered near bottom
    sub_filter = (
        f"subtitles='{srt_file}':force_style="
        "'Fontname=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF&,BackColour=&H80000000&,"
        "BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=35'"
    )

    burn_cmd = [
        FFMPEG_BIN,
        "-y",
        "-i", str(unsubbed_video),
        "-vf", sub_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "22",
        "-c:a", "copy",
        str(final_output)
    ]
    subprocess.run(burn_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    total_dur = get_audio_duration(final_output)
    file_size_mb = os.path.getsize(final_output) / (1024 * 1024)

    print("\n" + "=" * 70)
    print(f"✔ VIDEO GENERATION COMPLETE!")
    print(f"  Output Video:    {final_output}")
    print(f"  Duration:        {int(total_dur // 60)}m {int(total_dur % 60):02d}s (Limit: <5m)")
    print(f"  File Size:       {file_size_mb:.2f} MB")
    print(f"  Resolution:      1920x1080 Full HD (1080p)")
    print(f"  Audio:           Spoken Voice Narration (High Quality AAC)")
    print(f"  Closed Captions: Synchronized Burned-In Subtitles (SRT)")
    print("=" * 70)

if __name__ == "__main__":
    main()
