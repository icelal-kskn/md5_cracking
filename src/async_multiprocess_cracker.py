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


class AsnycPoster:
    def __init__(self,num_consumers,queue_size):
        self.queue = asyncio.Queue(queue_size)
        self.num_consumers = num_consumers
        self.semaphore = asyncio.Semaphore(1024) #1024 max limit of TCP connection 

    async def start(self):
        self.consumers = [
            asyncio.create_task(self._consumer())
            for _ in range(self.num_consumers)
        ]
        logging.info(f"Started {self.num_consumers} consumers")
    
    async def _post_password_with_limit(self,session,url,password):
        async with self.semaphore:
            return await self._post_password(session,url,password)
        
    async def _consumer(self):
        url = "http://127.0.0.1:5000"
        logging.info(f"Consumer started")
        async with aiohttp.ClientSession() as session:
            while True:
                logging.info(f"Consumer waiting for batch")
                batch = await self.queue.get()
                if batch is None:  # Çıkış sinyali
                    logging.info("Consumer shutting down")
                    self.queue.task_done()
                    break
                tasks = [self._post_password_with_limit(session, url, pw) for pw in batch]
                logging.info(f"Batch processing with {len(tasks)} tasks")
                results = await asyncio.gather(*tasks,return_exceptions=True)
                logging.info(f"Batch processed with results: {results}")
                self.queue.task_done()
    
    async def _post_password(self,session:aiohttp.ClientSession,url,password,retrie=3):
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
            except aiohttp.ClientError as e:
                logging.error(f"Error for {password}: {e}")
                continue
            except asyncio.TimeoutError as e:
                logging.error(f"Timeout for {password}: {e}")
                continue
            except PasswordFound as pf:
                logging.info(f"Password found: {pf.password}")
        return "Retrie"
    
    async def put(self,batch):
        while self.queue.full():
            logging.info(f"Queue is full. Waiting for 0.1 seconds")
            await asyncio.sleep(0.1)  
        await self.queue.put(batch)
        logging.info(f"Batch added to queue of size {len(batch)}")

    async def stop(self):
        for _ in range(self.num_consumers):
           await self.queue.put(None)
        if self.consumers:
            await asyncio.gather(*self.consumers)


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
        try:
            for batch in generate_combinations(charset,batch_size,length):
                logging.info(f"Sending batch of size {len(batch)}")
                pipe.send(batch)
        except StopIteration:
            continue
    



async def boss(min_length,max_length,num_workers):
    multiprocessing.set_start_method("spawn")
    processes = []
    pipes=[]
    active_pipes=[]
    consumer = AsnycPoster(100,4_000_000)
    await consumer.start()
    chunk_size = (max_length - min_length) // num_workers or 1
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
            active_pipes.append(parent_conn)
            p.start()
        
        try:
            while active_pipes:
                for pipe in active_pipes[:]:
                    try:
                        if pipe.poll():
                            passwords = pipe.recv()
                            await asyncio.sleep(0.01)
                            await consumer.put(passwords)
                            #Çok hızlı üretiyorum Ama Bu hızla tüketemiyorum
                    except OSError as e:
                        active_pipes.remove(pipe)
                        logging.info(f"Pipe removed: {e}")
                        continue
        finally:
            for pipe in pipes:
                pipe.close()
            await consumer.stop()
    
    except Exception as e:
        if isinstance(e, PasswordFound):
            logging.critical(f"Password found: {e.password}")
        for process in processes:
            process.terminate()
        for process in processes:
            process.join()

def main():
    password = asyncio.run(get_main())
    logging.info(f"Password: {password}")
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