import asyncio
import aiohttp
import logging
import os
import string
import multiprocessing

logging.basicConfig(
    format="%(levelname)s @ %(asctime)s : %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
    level=logging.INFO,
    handlers=[logging.FileHandler("requests.log", mode="w"), logging.StreamHandler()],
)

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
                return "Success"
            return "Failed" 
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logging.error(f"Error for {password}: {e}")
            continue
    return "Retrie"
    

async def post_main(password):
    url = "http://127.0.0.1:5000"
    async with aiohttp.ClientSession() as session:
        message = await post_password(session, url, password)
        return message



def generate_combinations(charset: str, length: int = 4):
    #modified version 
    current = [0] * length
    max_index = len(charset) - 1
    while True:
        result = ''.join(charset[i] for i in current)
        yield result

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

async def main(length):
    charset = string.digits 
    found_password = False  # Flag to track if password is found
    combination_count = len(charset) ** length
    print(f"Trying {combination_count} combinations of length {length}")

    try:        
        generator = generate_combinations(charset, length)
        batch_size = 500
        passwords = []
        retrie_passwords = []
        passwords += retrie_passwords.copy()

        for combination in generator:
            if found_password:  
                break

            retrie_passwords = []        
            passwords.append(combination)
            if len(passwords) > batch_size:
                for i in range(0, len(passwords), batch_size//10): 
                    # 1000er 10000er oluşturduğum batchleri 100er 100er kontrol ediyorum
                    # benim bilgisayarım için soft point burası
                    tasks = [post_main(password) for password in passwords[i:i + batch_size]]
                    results = await asyncio.gather(*tasks)
                    
                    
                    if "Success" in results:
                        found_password = True
                        success_index = results.index("Success")
                        logging.info(f"Password found: {passwords[success_index]}")
                        break

                    if "Retrie" in results:
                        retrie_passwords.append(passwords[results.index("Retrie")])

                    if "Failed" in results:
                        failed_index = results.index("Failed")
                        results.pop(failed_index) # For saving memory
                    
                passwords = []
                print(f"Retrie passwords: {retrie_passwords}")
        del passwords    
    except StopIteration:
        pass

    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Exiting...")

    if not found_password:
        logging.info("No password found")


def worker(start_length, end_length=None):
   if end_length is None:
       # Tek length için eski davranış
       asyncio.run(main(length=start_length))
   else:
       # Length aralığı için yeni davranış
       print(f"Worker started for lengths {start_length} to {end_length}")
       for length in range(start_length, end_length):
           asyncio.run(main(length=length))
           
if __name__ == "__main__":
   password = asyncio.run(get_main())
   print(f"Target hash: {password}")
   
   min_length = 8
   max_length = 15
   num_workers = os.cpu_count()
   processes = []
   
   chunk_size = (max_length - min_length) // num_workers

   if chunk_size == 0:
       chunk_size = 1
       
   try:
       for i in range(min_length, max_length, chunk_size):
           end = min(i + chunk_size, max_length)
           p = multiprocessing.Process(
               target=worker,
               args=(i, end)
           )
           processes.append(p)
           p.start()

       for process in processes:
           process.join()

   except KeyboardInterrupt:
       for process in processes:
           process.terminate()
       for process in processes:
           process.join()

