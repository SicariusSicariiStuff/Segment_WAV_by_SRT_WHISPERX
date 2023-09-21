# Splits a WAV or video file based on a subtitle SRT file, made for usage with WHISPERX to help with diarization

Usage:


```shell
segment_WAV_by_SRT.py WAV_file.wav SRT_file.srt 
```
```shell
segment_WAV_by_SRT.py some_video.mp4 SRT_file.srt 
```


BULK processing, spliting ALL *.wav files in the same dir, based on SRT files with the same names:

```shell
segment_WAV_by_SRT.py --all
```
For example, you have the files test1.wav, test1.srt, test2.wav, test2.srt... etc...
--all will split ALL of them, and create folders with each speaker based on the SRT file from WHISPERX.
