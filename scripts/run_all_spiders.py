import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import os

def run_spider(spider_name):
    countries = ['MX', 'CO', 'AR']
    for country in countries:
        cmd = [
            sys.executable,
            '-m',
            'src.orchestrator',
            'run-once',
            spider_name,
            '--country',
            country,
            '--limit',
            '15000',
            '--max-pages',
            '100',
            '--verbose'
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Print output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(f"[{spider_name}-{country}] {output.strip()}")
            
            # Get the return code
            return_code = process.poll()
            
            if return_code != 0:
                print(f"Error running {spider_name} for {country}. Return code: {return_code}")
                stderr = process.stderr.read()
                print(f"Error output: {stderr}")
                
        except Exception as e:
            print(f"Exception running {spider_name} for {country}: {str(e)}")

def main():
    spiders = [
        'infojobs',
        'elempleo',
        'bumeran',
        'computrabajo',
        'zonajobs',
        'magneto',
        'occmundial',
        'hiring_cafe',
        'indeed'
    ]
    
    # Run spiders in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=len(spiders)) as executor:
        executor.map(run_spider, spiders)

if __name__ == "__main__":
    main()