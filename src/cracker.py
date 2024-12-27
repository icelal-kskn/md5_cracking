import asyncio
import logging
import aiohttp
import string
import multiprocessing
import os
import time

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

async def post_password(session:aiohttp.ClientSession,url,password,retrie=3):
    for _ in range(retrie):
        try:
            response = await session.post(
                f"{url}/check_password",
                json={"password": password}
            )
            response.raise_for_status()
            logging.info(f"Request returned for {password} with status code {response.status}")
            message = (await response.json()).get("message")
            if message == "Success":
                logging.info(f"Password {password} is correct")
                raise PasswordFound(password)
            return "Failed" 
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logging.error(f"Error for {password}: {e}")
            continue
    return "Retrie"

async def post_main(queue: multiprocessing.Queue):
    url = "http://127.0.0.1:5000"
    async with aiohttp.ClientSession() as session:
        while True:
            batch = queue.get()
            if batch is None:
                break
            logging.info(f"Consumer received batch of size {len(batch)}")
            tasks = [asyncio.create_task(post_password(session, url, pw)) for pw in batch]
            await asyncio.gather(*tasks)

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

def worker(start_length,end_length,pipe):
    charset = string.digits+string.ascii_letters
    logging.info(f"Worker started for lengths {start_length} to {end_length}")
    
    for length in range(start_length, end_length):
        combination_count = len(charset) ** length
        batch_size = min(1_000_000, combination_count)
        logging.info(f"Length {length} Combinations {combination_count} Batch size {batch_size}")
        for batch in generate_combinations(charset,batch_size,length):
            logging.info(f"Sending batch of size {len(batch)}")
            pipe.send(batch)




async def boss(min_length,max_length,num_workers):
    processes = []
    pipes=[]
    chunk_size = (max_length - min_length) // num_workers or 1
    multiprocessing.set_start_method("spawn")
    try:
        for i in range(min_length, max_length, chunk_size):
            parent_conn, child_conn = multiprocessing.Pipe(False)
            end = min(i + chunk_size, max_length)
            p = multiprocessing.Process(
                target=worker,
                args=(i, end, child_conn),
                name=f"Worker-{i}",
            )
            processes.append(p)
            pipes.append(parent_conn)
            p.start()
        
        for process in processes:
            process.join()
        

        while True:
            for pipe in pipes:
                if pipe.poll():
                    passwords = pipe.recv()
                    logging.info(f"Received batch of size {len(passwords)}")
                    #Çok hızlı üretiyorum Ama Bu hızla tüketemiyorum

    
    except Exception as e:
        if isinstance(e, PasswordFound):
            logging.critical(f"Password found: {e.password}")
        print(e)
        for process in processes:
            process.terminate()
        for process in processes:
            process.join()

def main():
    num_workers = os.cpu_count()
    logging.info(f"Number of workers: {num_workers}")
    min_length = 8
    max_length = 16

    try:
        asyncio.run(boss(min_length, max_length, num_workers))
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Exiting...")
    except PasswordFound as e:
        logging.critical(f"Password found: {e.password}")
        


if __name__ == "__main__":
    start_time = time.time()
    main()
    logging.info(f"Time taken: {time.time()-start_time}")