import asyncio
import logging
import aiohttp
import string
import multiprocessing
import os
import time
import hashlib

logging.basicConfig(
    format="%(levelname)s @ %(asctime)s : %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
    level=logging.INFO,
    handlers=[logging.FileHandler("requests.log", mode="w"), logging.StreamHandler()],
)
class PasswordFound(Exception):
    def __init__(self, password):
        self.password = password
     
async def get_password(session:aiohttp.ClientSession,url):
        response = await session.get(f"{url}/get_password")
        password = (await response.json()).get("password")
        return password

async def get_main():
    url = "http://127.0.0.1:5000"
    async with aiohttp.ClientSession() as session:
        password = await get_password(session, url)
        return password
    
async def post_main(password):
    url = "http://127.0.0.1:5000"
    async with aiohttp.ClientSession() as session:
        response = await session.post(f"{url}/check_password", json={"password": password})
        result = await response.json()
        logging.info(result)


def generate_combinations(charset: str,batch_size, length: int = 4):
    results = []
    current = [0] * length
    max_index = len(charset) - 1
    while True:
        result = ''.join(charset[i] for i in current)
        results.append(result)
        if len(results) == batch_size:
            yield results
            results = []

        pos= length -1
        while pos >= 0:
            if current[pos] < max_index:
                current[pos] += 1
                break
            else:
                current[pos] = 0
                pos -= 1
        if pos < 0:
            break

def worker(start_length,end_length,get_password_,pipe):
    charset = string.digits+string.ascii_letters
    logging.info(f"Worker started for lengths {start_length} to {end_length}")
    
    for length in range(start_length, end_length):
        combination_count = len(charset) ** length
        batch_size = min(1_000_000, combination_count)
        logging.info(f"Length {length} Combinations {combination_count} Batch size {batch_size}")
        try:
            for batch in generate_combinations(charset,batch_size,length):
                hashed_batch = [hashlib.md5(comb.encode()).hexdigest() for comb in batch]
                for password in hashed_batch:
                    logging.info(f"Checking password: {batch[hashed_batch.index(password)]}")
                    if password == get_password_:
                        pipe.send(password)
        except StopIteration:
            continue
    



async def boss(get_password,min_length,max_length,num_workers):
    multiprocessing.set_start_method("spawn")
    processes = []
    pipes=[]
    active_pipes=[]
    chunk_size = (max_length - min_length) // num_workers or 1
    try:
        for i in range(min_length, max_length, chunk_size):
            parent_conn, child_conn = multiprocessing.Pipe(False)
            end = min(i + chunk_size, max_length)
            p = multiprocessing.Process(
                target=worker,
                args=(i, end,get_password, child_conn),
                name=f"Worker-{i}",
            )
            processes.append(p)
            pipes.append(parent_conn)
            active_pipes.append(parent_conn)
            p.start()
        
        try:
            while active_pipes:
                for pipe in active_pipes[:]:
                    try:
                        if pipe.poll():
                            found_password = pipe.recv()
                            raise PasswordFound(found_password)
                        
                    except OSError as e:
                        active_pipes.remove(pipe)
                        logging.info(f"Pipe removed: {e}")
                        continue
        finally:
            for pipe in pipes:
                pipe.close()
    
    except Exception as e:
        if isinstance(e, PasswordFound):
            logging.critical(f"Password found: {e.password}")
            post_main(e.password)
        for process in processes:
            process.terminate()
        for process in processes:
            process.join()

def main():
    get_password = asyncio.run(get_main())
    logging.info(f"Password: {get_password}")
    num_workers = os.cpu_count()
    logging.info(f"Number of workers: {num_workers}")
    min_length = 8
    max_length = 16

    try:
        asyncio.run(boss(get_password,min_length, max_length, num_workers))
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Exiting...")
    except PasswordFound as e:
        logging.critical(f"Password found: {e.password}")
        


if __name__ == "__main__":
    start_time = time.time()
    main()
    logging.info(f"Time taken: {time.time()-start_time}")