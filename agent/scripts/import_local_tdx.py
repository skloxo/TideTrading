#!/usr/bin/env python3
import logging
import struct
import sqlite3
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('import_local_tdx')

def get_market_db_path():
    base = Path.home() / '.vibe-trading-cnx'
    base.mkdir(parents=True, exist_ok=True)
    return base / 'stocks_market.db'

def parse_day_file(file_path):
    records = []
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        record_size = 32
        num_records = len(data) // record_size
        for i in range(num_records):
            pos = i * record_size
            chunk = data[pos : pos + record_size]
            fields = struct.unpack('<IIIIIfII', chunk)
            dt = str(fields[0])
            if len(dt) == 8:
                date_str = f'{dt[:4]}-{dt[4:6]}-{dt[6:]}'
            else:
                continue
            op, hi, lo, cl = fields[1]/100.0, fields[2]/100.0, fields[3]/100.0, fields[4]/100.0
            amount, volume = float(fields[5]), int(fields[6])
            records.append((date_str, op, hi, lo, cl, volume, amount))
    except Exception as e:
        logger.debug(f'Error parsing {file_path}: {e}')
    return records

def import_market_data(tdx_path):
    db_path = get_market_db_path()
    logger.info('='*60)
    logger.info('本地通达信数据导入器')
    logger.info(f'  通达信 vipdoc 路径: {tdx_path}')
    logger.info(f'  目标数据库 (Shared): {db_path}')
    logger.info('='*60)
    tdx_root = Path(tdx_path)
    if not tdx_root.exists():
        logger.error(f'本地通达信 vipdoc 目录未找到: {tdx_root}')
        return
    day_files = []
    for market in ['sh', 'sz', 'bj', 'ds']:
        lday_dir = tdx_root / market / 'lday'
        if lday_dir.exists():
            files = list(lday_dir.glob('*.day'))
            logger.info(f'  发现 {market.upper()} 市场日线文件: {len(files)} 个')
            day_files.extend([(f, market.upper()) for f in files])
    if not day_files:
        logger.warning('未找到任何 .day 数据文件。请确认通达信已下载日线数据且路径正确。')
        return
    conn = sqlite3.connect(str(db_path))
    conn.execute('''
        CREATE TABLE IF NOT EXISTS kline_daily (
            code TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER, amount REAL,
            PRIMARY KEY (code, date)
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_kline_daily_code ON kline_daily (code)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_kline_daily_date ON kline_daily (date)')
    conn.commit()
    total_inserted = 0
    start_time = time.time()
    for idx, (file_path, market) in enumerate(day_files, 1):
        filename = file_path.stem
        code = filename[2:] if len(filename) > 2 else filename
        if not code.isdigit(): continue
        records = parse_day_file(file_path)
        if not records: continue
        db_records = [(code, r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in records]
        try:
            conn.executemany('INSERT OR REPLACE INTO kline_daily (code, date, open, high, low, close, volume, amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', db_records)
            conn.commit()
            total_inserted += len(db_records)
        except Exception as e:
            logger.error(f'Failed to write stock {code}: {e}')
        if idx % 100 == 0 or idx == len(day_files):
            elapsed = time.time() - start_time
            speed = total_inserted / elapsed if elapsed > 0 else 0
            logger.info(f'  进度: [{idx}/{len(day_files)}] 股票 | 累计导入 K 线: {total_inserted:,} 条 | 速度: {speed:.1f} 条/秒')
    logger.info('正在优化数据库空间 (VACUUM)...')
    conn.execute('VACUUM')
    conn.close()
    total_time = time.time() - start_time
    logger.info('='*60)
    logger.info(f'导入完成！总耗时: {total_time:.1f} 秒，总日 K 线: {total_inserted:,} 条')
    logger.info('='*60)
if __name__ == '__main__':
    import_market_data('/home/vibe/.vibe-trading-cnx/vipdoc/vipdoc')



