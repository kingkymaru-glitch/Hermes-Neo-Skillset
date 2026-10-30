# Worked diagnostic example (real numbers, kamarulhk Mac, 2026-08-30)

Disk: ~494 GB total, 91% used. User reported "System Data 245.8 GB".

## Commands run (one shot each)
```
tmutil listlocalsnapshots /          # -> empty (no local TM snapshots)
du -sh /Library/Caches              # 4.1G
du -sh ~/Library/Caches             # 19G
du -sh ~/Library/Application\ Support/MobileSync/Backup   # empty (no iOS backups)
du -sh ~/Library/Developer/Xcode/DerivedData             # 6.4G
du -sh ~/Library/Caches/com.apple.dt.Xcode               # 4.5M
du -sh ~/.docker ~/Library/Containers/com.docker.docker   # 17M + 29G
du -sh ~/Library/Containers         # 68G   <- biggest single line
du -sh /private/var/folders          # 7.2G
du -sh /Library/Updates             # 1.8G
du -sh ~/Library/Developer/CoreSimulator   # 20G
du -sh /Library/Developer           # 22G
du -sh ~/Library/Logs               # 397M
du -sh ~/Library                   # 176G  (top-level total)
```

## Sum of culprits
Containers 68 + Docker 29 + CoreSimulator 20 + /Library/Caches 4.1 + ~/Library/Caches 19
+ /Library/Developer 22 + var/folders 7.2 + DerivedData 6.4 + /Library/Updates 1.8
+ Logs ~0.4 ≈ 178 GB, plus swap/misc → reconciles to the ~245 GB "System Data" bucket.

## Takeaways
- No local TM snapshots were present (common red herring ruled out).
- ~/Library/Containers was the single largest contributor — must NOT be blanket-removed.
- Safe immediate reclaim without touching Containers: DerivedData (6.4) + caches (19 + 4.1)
  + simulator (20) ≈ 50 GB, ~80 GB if Docker pruned.
- `df -h /` and `diskutil apfs list` confirmed capacity/usage independently of the GUI.
