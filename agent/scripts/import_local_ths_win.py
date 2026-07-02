#!/usr/bin/env python3
"""
import_local_ths_win.py — 同花顺本地数据高速导入器
读取 Windows 本地 C:/同花顺软件/同花顺/history 下的日K线数据，
解析二进制 hd1.0 格式（176 字节记录），高速批量导入共享数据库 stocks_market.db。
"""
import logging
import os
import struct
import sqlite3
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('import_local_ths_win')

def parse_ths_day_file(file_path):
    records = []
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        offset = 192
        record_size = 176
        num_records = (len(data) - offset) // record_size
        
        for i in range(num_records):
            pos = offset + i * record_size
            chunk = data[pos : pos + 28]  # Only read first 28 bytes (7 fields)
            fields = struct.unpack('<IIIIIII', chunk)
            
            dt = str(fields[0])
            if len(dt) == 8:
                date_str = f'{dt[:4]}-{dt[4:6]}-{dt[6:]}'
            else:
                continue
            
            # Formula: (val - 0xC0000000) / 10000.0
            op = (fields[1] - 0xC0000000) / 10000.0 if fields[1] >= 0xC0000000 else fields[1] / 100.0
            hi = (fields[2] - 0xC0000000) / 10000.0 if fields[2] >= 0xC0000000 else fields[2] / 100.0
            lo = (fields[3] - 0xC0000000) / 10000.0 if fields[3] >= 0xC0000000 else fields[3] / 100.0
            cl = (fields[4] - 0xC0000000) / 10000.0 if fields[4] >= 0xC0000000 else fields[4] / 100.0
            
            amount = float(fields[5])  # in Yuan
            volume = int(fields[6])   # in Shares
            
            records.append((date_str, op, hi, lo, cl, volume, amount))
    except Exception as e:
        logger.debug(f'Error parsing THS file {file_path}: {e}')
    return records

def import_ths_data(ths_history_dir, db_path):
    logger.info('='*60)
    logger.info('同花顺本地数据高速导入器')
    logger.info(f'  同花顺 history 路径: {ths_history_dir}')
    logger.info(f'  共享数据库 路径: {db_path}')
    logger.info('='*60)

    history_root = Path(ths_history_dir)
    if not history_root.exists():
        logger.error(f'同花顺历史数据目录不存在: {history_root}')
        return

    day_files = []
    for market, exchange in [('shase', 'SH'), ('sznse', 'SZ')]:
        day_dir = history_root / market / 'day'
        if day_dir.exists():
            files = list(day_dir.glob('*.day'))
            logger.info(f'  发现 {exchange} 市场日线文件: {len(files)} 个')
            day_files.extend([(f, exchange) for f in files])

    if not day_files:
        logger.warning('未找到同花顺 K 线数据，请确认下载完成。')
        return

    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS kline_daily (
            code TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER, amount REAL,
            PRIMARY KEY (code, date)
        )
    ''')
    conn.commit()

    total_inserted = 0
    start_time = time.time()

    for idx, (file_path, exchange) in enumerate(day_files, 1):
        filename = file_path.stem
        code = filename
        if not code.isdigit():
            continue
        
        records = parse_ths_day_file(file_path)
        if not records:
            continue

        db_records = [(code, r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in records]
        
        try:
            conn.executemany('''
                INSERT OR REPLACE INTO kline_daily (code, date, open, high, low, close, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', db_records)
            conn.commit()
            total_inserted += len(db_records)
        except Exception as e:
            logger.error(f'写入 {code} 失败: {e}')

        if idx % 100 == 0 or idx == len(day_files):
            elapsed = time.time() - start_time
            speed = total_inserted / elapsed if elapsed > 0 else 0
            logger.info(f'  进度: [{idx}/{len(day_files)}] 股票 | 累计导入日K线: {total_inserted:,} 条 | 速度: {speed:.1f} 条/秒')

    logger.info('正在优化数据库空间 (VACUUM)...')
    conn.execute('VACUUM')
    conn.close()
    
    total_time = time.time() - start_time
    logger.info('='*60)
    logger.info(f'同花顺本地数据导入完成！')
    logger.info(f'  总耗时: {total_time:.1f} 秒')
    logger.info(f'  总导入日 K 线: {total_inserted:,} 条')
    logger.info('='*60)

if __name__ == '__main__':
    import glob
    # BFS scan C: drive up to 3 levels deep to locate the true path of THS history folder
    ths_dir = None
    for d1 in glob.glob("C:/*"):
        try:
            if not os.path.isdir(d1):
                continue
            p1 = Path(d1) / "history"
            if (p1 / "sznse" / "day").exists():
                ths_dir = str(p1)
                break
                
            # Scan level 2
            for d2 in glob.glob(d1 + "/*"):
                try:
                    if not os.path.isdir(d2):
                        continue
                    p2 = Path(d2) / "history"
                    if (p2 / "sznse" / "day").exists():
                        ths_dir = str(p2)
                        break
                except Exception:
                    pass
            if ths_dir:
                break
        except Exception:
            pass
            
    if not ths_dir:
        # Fallback
        ths_dir = "C:/同花顺软件/同花顺/history"
        
    wsl_db = "//wsl.localhost/Ubuntu-24.04/home/skloxo/.vibe-trading-cnx/stocks_market.db"
    import_ths_data(ths_dir, wsl_db)



