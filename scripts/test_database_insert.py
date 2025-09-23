#!/usr/bin/env python3
"""
Test database insertion with fake scraper data.
"""

import os
import sys
import psycopg2
import json
import hashlib
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def create_test_connection():
    """Create a test database connection."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            database="labor_observatory",
            user="labor_user",
            password="your_password"
        )
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None

def test_insert_fake_job():
    """Test inserting a fake job record."""
    conn = create_test_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create fake job data that matches scraper output format
        fake_job_data = {
            "portal": "bumeran",
            "country": "MX",
            "url": "https://www.bumeran.com.mx/empleos/desarrollador-python-12345",
            "title": "Desarrollador Python Senior",
            "company": "Tech Solutions MX",
            "location": "Ciudad de México",
            "description": "Buscamos un desarrollador Python con experiencia en Django, Flask y bases de datos. Responsable de desarrollar aplicaciones web escalables y mantener sistemas existentes.",
            "requirements": "Python, Django, Flask, PostgreSQL, Git, Docker, 3+ años de experiencia",
            "salary_raw": "$25,000 - $35,000 MXN",
            "contract_type": "Tiempo completo",
            "remote_type": "Híbrido",
            "posted_date": "2025-01-20"
        }
        
        # Generate content hash
        content = f"{fake_job_data['title']}{fake_job_data['description']}{fake_job_data.get('requirements', '')}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        fake_job_data["content_hash"] = content_hash
        
        # Insert the job
        insert_query = """
            INSERT INTO raw_jobs (
                portal, country, url, title, company, location, description, 
                requirements, salary_raw, contract_type, remote_type, 
                posted_date, content_hash
            ) VALUES (
                %(portal)s, %(country)s, %(url)s, %(title)s, %(company)s, 
                %(location)s, %(description)s, %(requirements)s, %(salary_raw)s, 
                %(contract_type)s, %(remote_type)s, %(posted_date)s, %(content_hash)s
            ) RETURNING job_id;
        """
        
        cursor.execute(insert_query, fake_job_data)
        job_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"✅ Fake job inserted successfully with ID: {job_id}")
        
        # Verify the insert by querying the record
        cursor.execute("""
            SELECT job_id, portal, country, title, company, location, 
                   description, requirements, salary_raw, contract_type, 
                   remote_type, posted_date, scraped_at, content_hash
            FROM raw_jobs 
            WHERE job_id = %s;
        """, (job_id,))
        
        inserted_job = cursor.fetchone()
        
        if inserted_job:
            print("✅ Job verification successful - record found in database")
            print(f"   Job ID: {inserted_job[0]}")
            print(f"   Portal: {inserted_job[1]}")
            print(f"   Country: {inserted_job[2]}")
            print(f"   Title: {inserted_job[3]}")
            print(f"   Company: {inserted_job[4]}")
            print(f"   Location: {inserted_job[5]}")
            print(f"   Posted Date: {inserted_job[11]}")
            print(f"   Scraped At: {inserted_job[12]}")
            return True
        else:
            print("❌ Job verification failed - record not found")
            return False
            
    except Exception as e:
        print(f"❌ Insert test failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def test_batch_insert():
    """Test inserting multiple fake jobs."""
    conn = create_test_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create multiple fake jobs
        fake_jobs = [
            {
                "portal": "elempleo",
                "country": "CO",
                "url": "https://www.elempleo.com/co/ofertas/analista-datos-67890",
                "title": "Analista de Datos",
                "company": "Data Corp Colombia",
                "location": "Bogotá",
                "description": "Analizar datos de clientes y generar reportes para la toma de decisiones estratégicas.",
                "requirements": "SQL, Python, Power BI, Excel avanzado, 2+ años experiencia",
                "salary_raw": "$3,500,000 - $4,500,000 COP",
                "contract_type": "Tiempo completo",
                "remote_type": "Presencial",
                "posted_date": "2025-01-19"
            },
            {
                "portal": "computrabajo",
                "country": "AR",
                "url": "https://www.computrabajo.com.ar/ofertas/desarrollador-fullstack-11111",
                "title": "Desarrollador Full Stack",
                "company": "Startup Argentina",
                "location": "Buenos Aires",
                "description": "Desarrollar aplicaciones web completas desde frontend hasta backend.",
                "requirements": "React, Node.js, MongoDB, AWS, 4+ años experiencia",
                "salary_raw": "$150,000 - $200,000 ARS",
                "contract_type": "Tiempo completo",
                "remote_type": "Remoto",
                "posted_date": "2025-01-18"
            }
        ]
        
        inserted_count = 0
        
        for job_data in fake_jobs:
            # Generate content hash
            content = f"{job_data['title']}{job_data['description']}{job_data.get('requirements', '')}"
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            job_data["content_hash"] = content_hash
            
            # Insert the job
            insert_query = """
                INSERT INTO raw_jobs (
                    portal, country, url, title, company, location, description, 
                    requirements, salary_raw, contract_type, remote_type, 
                    posted_date, content_hash
                ) VALUES (
                    %(portal)s, %(country)s, %(url)s, %(title)s, %(company)s, 
                    %(location)s, %(description)s, %(requirements)s, %(salary_raw)s, 
                    %(contract_type)s, %(remote_type)s, %(posted_date)s, %(content_hash)s
                ) RETURNING job_id;
            """
            
            try:
                cursor.execute(insert_query, job_data)
                job_id = cursor.fetchone()[0]
                inserted_count += 1
                print(f"✅ Inserted job {inserted_count}: {job_data['title']} (ID: {job_id})")
            except psycopg2.IntegrityError:
                print(f"⚠️  Duplicate job skipped: {job_data['title']}")
                conn.rollback()
                continue
        
        conn.commit()
        print(f"✅ Batch insert completed: {inserted_count} jobs inserted")
        
        # Verify total count
        cursor.execute("SELECT COUNT(*) FROM raw_jobs;")
        total_count = cursor.fetchone()[0]
        print(f"✅ Total jobs in database: {total_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch insert test failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def test_duplicate_handling():
    """Test handling of duplicate jobs (same content_hash)."""
    conn = create_test_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create a job with a known hash
        test_job = {
            "portal": "test_portal",
            "country": "CO",
            "url": "https://test.com/duplicate-test",
            "title": "Duplicate Test Job",
            "company": "Test Company",
            "location": "Test City",
            "description": "This is a test job for duplicate handling.",
            "requirements": "Testing skills",
            "content_hash": "duplicate_test_hash_12345"
        }
        
        # First insert should succeed
        insert_query = """
            INSERT INTO raw_jobs (
                portal, country, url, title, company, location, description, 
                requirements, content_hash
            ) VALUES (
                %(portal)s, %(country)s, %(url)s, %(title)s, %(company)s, 
                %(location)s, %(description)s, %(requirements)s, %(content_hash)s
            ) RETURNING job_id;
        """
        
        cursor.execute(insert_query, test_job)
        job_id_1 = cursor.fetchone()[0]
        conn.commit()
        print(f"✅ First insert successful: {job_id_1}")
        
        # Second insert with same hash should fail
        try:
            cursor.execute(insert_query, test_job)
            job_id_2 = cursor.fetchone()[0]
            conn.commit()
            print(f"❌ Duplicate insert should have failed but succeeded: {job_id_2}")
            return False
        except psycopg2.IntegrityError as e:
            conn.rollback()
            print(f"✅ Duplicate insert correctly rejected: {e}")
            return True
            
    except Exception as e:
        print(f"❌ Duplicate handling test failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("Testing database insertion with fake scraper data...")
    print("=" * 60)
    
    # Test single job insert
    print("\n1. Testing single job insert:")
    success1 = test_insert_fake_job()
    
    # Test batch insert
    print("\n2. Testing batch insert:")
    success2 = test_batch_insert()
    
    # Test duplicate handling
    print("\n3. Testing duplicate handling:")
    success3 = test_duplicate_handling()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Single insert: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"Batch insert:  {'✅ PASS' if success2 else '❌ FAIL'}")
    print(f"Duplicate handling: {'✅ PASS' if success3 else '❌ FAIL'}")
    
    if all([success1, success2, success3]):
        print("\n🎉 All database insertion tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
