import requests
import json

url = 'https://carbify-io.onrender.com/api'
s = requests.Session()

print("Registering...")
r1 = s.post(f'{url}/auth/register', json={'username': 'testuser99', 'email': 't99@test.com', 'password': 'password123'})
print('Register:', r1.status_code, r1.text)

print("Logging in...")
r2 = s.post(f'{url}/auth/login', json={'username': 'testuser99', 'password': 'password123'})
token = r2.json().get('access_token') if r2.status_code == 200 else None
print('Login:', r2.status_code)

if token:
    headers = {'Authorization': f'Bearer {token}'}

    print("Fetching analytics before logging...")
    r_empty = s.get(f'{url}/analytics', headers=headers)
    print('Empty Analytics:', r_empty.status_code, r_empty.text)

    print("Logging emissions...")
    log_data = {
        'electricity_kwh': 10, 'gas_kwh': 5, 'petrol_car_km': 10, 'diesel_car_km': 0, 
        'electric_car_km': 0, 'public_transit_km': 0, 'flights_km': 0, 
        'diet_type': 'meat_heavy', 'waste_kg': 2, 'recycling_rate': 0.5
    }
    r3 = s.post(f'{url}/calculator/log', json=log_data, headers=headers)
    print('Log:', r3.status_code, r3.text)

    print("Fetching analytics after logging...")
    r4 = s.get(f'{url}/analytics', headers=headers)
    print('Analytics:', r4.status_code, r4.text)
