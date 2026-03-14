"""
Raw SQL proof - Query database directly
"""
import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

print("\n" + "="*80)
print("RAW SQL QUERY - DIRECT DATABASE PROOF")
print("="*80 + "\n")

# Query service request
cursor.execute("""
    SELECT id, title, workers_needed, total_price, status, created_at
    FROM jobs_servicerequest 
    WHERE workers_needed >= 2 
    ORDER BY id DESC 
    LIMIT 1
""")

request = cursor.fetchone()
if request:
    req_id, title, workers_needed, total_price, status, created_at = request
    
    print(f"📋 SERVICE REQUEST TABLE:")
    print(f"   ID: {req_id}")
    print(f"   Title: {title}")
    print(f"   Workers Needed: {workers_needed}")
    print(f"   Total Price: {total_price} TSH")
    print(f"   Status: {status}")
    print(f"   Created: {created_at}")
    
    # Query assignments
    cursor.execute(f"""
        SELECT id, assignment_number, status, worker_payment
        FROM jobs_servicerequestassignment 
        WHERE service_request_id = {req_id}
        ORDER BY assignment_number
    """)
    
    assignments = cursor.fetchall()
    
    print(f"\n📋 ASSIGNMENTS TABLE ({len(assignments)} records):")
    for assignment in assignments:
        ass_id, ass_num, ass_status, payment = assignment
        icon = {'accepted': '✅', 'rejected': '❌', 'pending': '⏳'}.get(ass_status, '❓')
        print(f"   {icon} ID {ass_id}: Assignment #{ass_num} | {ass_status.upper()} | {payment} TSH")
    
    print("\n" + "="*80)
    print("✅ THIS IS RAW DATA FROM SQLITE DATABASE FILE")
    print("✅ NOT MOCK DATA, NOT FAKE DATA - REAL DATABASE RECORDS")
    print("="*80 + "\n")

conn.close()
