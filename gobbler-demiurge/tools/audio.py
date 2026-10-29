"""Master the two music beds for the page: set each to the same integrated loudness, encode AAC, and write the manifest (prompts, seeds, loudness, sha256).

    python3 -I tools/audio.py --src DIR [--out assets/audio]       (DIR holds cosmos-<seed>.wav and village-<seed>.wav; needs ffmpeg)

The two clips came out of a text-to-music model, three seeds for each zone, 32.77 s of stereo at 48 kHz, so the sources are not reproduced here: assets/audio/ keeps what the page
plays. Choosing between seeds was done on measures first (integrated loudness, loudness range, how alike the last and the first 4 s are, which is what a crossfaded loop joins) and then
by listening reviewers; the chosen seed and the numbers are in manifest.json. The page loops a bed by crossfading two overlapping copies, so codec padding does not matter.
"""
import argparse, hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET_LUFS = -26.0                       # a bed sits under the picture: quiet by design, the listener's own volume does the rest
BITRATE = '96k'
TRIM_S = 0.01                             # every source clip starts with the same click (the first 12 stereo frames are identical in all six clips, about 0.2 ms, peak -1.4 dBFS): cut it
NEG = 'vocals, singing, voice, drums, percussion, beat, rhythmic pulse, bass drop, distortion, harsh, noisy, sudden changes, crescendo, climax, ending'
ZONES = {
    'cosmos': dict(seed=101, plays='the bird, the Sun, the ribcage and out to the Earth',
                   prompt='Vast cinematic ambient music for a slow flight through a golden constellation: warm evolving synthesizer pads, a deep cello and low brass drone, soft glass bells and harp harmonics far away, '
                          'a sense of awe and reverence, very slow, spacious reverb, no drums, no vocals, no melody hooks, a steady texture that can loop'),
    'village': dict(seed=101, plays='down in the village, from the orbit stop to a villager',
                    prompt='Gentle pastoral ambient music for a small village at golden hour: soft plucked harp, kalimba and music box playing a faint simple melody, a warm low string drone underneath, a little breathy wooden '
                           'flute, intimate, calm and hopeful, slow, no drums, no vocals, a steady texture that can loop'),
}


def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def ffmpeg(*a): return subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-y', *a], capture_output=True, text=True)


def loudness(path, ss=None, t=None):
    """EBU R128 integrated loudness (LUFS), loudness range (LU) and sample peak (dBFS) of a file or of a window of it"""
    cmd = (['-ss', str(ss)] if ss is not None else []) + (['-t', str(t)] if t is not None else []) + ['-i', path, '-filter_complex', 'ebur128=peak=sample', '-f', 'null', '-']
    r = ffmpeg(*cmd).stderr; last = r[r.rfind('Summary:'):]
    g = lambda pat: float(re.search(pat, last).group(1))
    return dict(I=g(r'I:\s+(-?[\d.]+) LUFS'), LRA=g(r'LRA:\s+(-?[\d.]+) LU'), peak=g(r'Peak:\s+(-?[\d.]+) dBFS'))


def master(src, dst):
    m = loudness(src); gain = round(TARGET_LUFS - m['I'], 1)
    r = ffmpeg('-i', src, '-af', 'atrim=start=%s,asetpts=PTS-STARTPTS,volume=%sdB' % (TRIM_S, gain), '-map_metadata', '-1', '-fflags', '+bitexact', '-c:a', 'aac', '-b:a', BITRATE, '-ar', '48000', '-movflags', '+faststart', dst)
    if r.returncode: sys.exit('ffmpeg failed:\n' + r.stderr[-800:])
    return m, gain


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', path], capture_output=True, text=True)
    return round(float(r.stdout), 3)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--src', required=True); ap.add_argument('--out', default=os.path.join(HERE, '..', 'assets', 'audio'))
    a = ap.parse_args(); out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True); man = dict(target_lufs=TARGET_LUFS, trim_start_s=TRIM_S, codec='AAC-LC %s stereo 48 kHz' % BITRATE, loop='the page crossfades two overlapping copies (equal power, 4 s)', beds={})
    for zone, z in ZONES.items():
        src = os.path.join(a.src, '%s-%d.wav' % (zone, z['seed'])); dst = os.path.join(out, zone + '.m4a')
        if not os.path.isfile(src): sys.exit('missing source: ' + src)
        m, gain = master(src, dst); o = loudness(dst); head, tail = loudness(dst, 0, 4), loudness(dst, duration(dst) - 4.0, 4)
        man['beds'][zone] = dict(file=zone + '.m4a', plays=z['plays'], prompt=z['prompt'], negative_prompt=NEG, seed=z['seed'], seconds=duration(dst),
                                 source=dict(sha256=sha(src), lufs=m['I'], lra=m['LRA'], peak_dbfs=m['peak']), gain_db=gain,
                                 mastered=dict(lufs=o['I'], lra=o['LRA'], peak_dbfs=o['peak'], seam_dlufs=round(abs(head['I'] - tail['I']), 2)), bytes=os.path.getsize(dst), sha256=sha(dst))
        print(zone, json.dumps(man['beds'][zone]['mastered']), os.path.getsize(dst), 'B')
    json.dump(man, open(os.path.join(out, 'manifest.json'), 'w'), indent=1); print('wrote', os.path.join(out, 'manifest.json'))


if __name__ == '__main__':
    main()
