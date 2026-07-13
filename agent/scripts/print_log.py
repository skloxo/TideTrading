lines = open('/tmp/full_sync.log', encoding='utf-8', errors='ignore').readlines()
non_empty = [l.strip() for l in lines if l.strip()]
for l in non_empty[-30:]:
    print(l)
