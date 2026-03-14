"""
Quick test to verify assignment acceptance works
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_connect.settings')
django.setup()

from jobs.service_request_serializers import AssignmentResponseSerializer

print("=" * 60)
print("TESTING ASSIGNMENT RESPONSE SERIALIZER")
print("=" * 60)

# Test 1: Accept with notes (mobile app scenario)
print("\n✅ Test 1: Accept with notes (mobile app sends this)")
data1 = {'accepted': True, 'notes': 'I can start tomorrow'}
serializer1 = AssignmentResponseSerializer(data=data1)
if serializer1.is_valid():
    print(f"   ✓ Valid! Data: {serializer1.validated_data}")
else:
    print(f"   ✗ FAILED! Errors: {serializer1.errors}")

# Test 2: Accept without notes
print("\n✅ Test 2: Accept without notes")
data2 = {'accepted': True}
serializer2 = AssignmentResponseSerializer(data=data2)
if serializer2.is_valid():
    print(f"   ✓ Valid! Data: {serializer2.validated_data}")
else:
    print(f"   ✗ FAILED! Errors: {serializer2.errors}")

# Test 3: Reject with reason
print("\n✅ Test 3: Reject with reason")
data3 = {'accepted': False, 'rejection_reason': 'Already booked'}
serializer3 = AssignmentResponseSerializer(data=data3)
if serializer3.is_valid():
    print(f"   ✓ Valid! Data: {serializer3.validated_data}")
else:
    print(f"   ✗ FAILED! Errors: {serializer3.errors}")

# Test 4: Reject without reason (should fail)
print("\n❌ Test 4: Reject without reason (should fail)")
data4 = {'accepted': False}
serializer4 = AssignmentResponseSerializer(data=data4)
if serializer4.is_valid():
    print(f"   ✗ SHOULD HAVE FAILED! Data: {serializer4.validated_data}")
else:
    print(f"   ✓ Correctly failed! Errors: {serializer4.errors}")

print("\n" + "=" * 60)
print("SUMMARY:")
print("=" * 60)
if (serializer1.is_valid() and serializer2.is_valid() and 
    serializer3.is_valid() and not serializer4.is_valid()):
    print("✅ ALL TESTS PASSED! Worker can accept/reject assignments!")
    print("✅ Mobile app accept with notes: WORKS")
    print("✅ Accept without notes: WORKS")
    print("✅ Reject with reason: WORKS")
    print("✅ Reject without reason: CORRECTLY FAILS")
else:
    print("❌ SOME TESTS FAILED! Check output above.")
print("=" * 60)
