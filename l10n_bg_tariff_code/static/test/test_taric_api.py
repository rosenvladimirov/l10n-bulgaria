#!/usr/bin/env python3
"""
UK Trade Tariff API Test Script (UPDATED)
Тестване на UK Trade Tariff REST API за TARIC данни
"""

import requests
import json
import time
from datetime import datetime

# Тестови CN кодове (8-цифрени, по-надеждни)
TEST_CODES_8_DIGIT = [
    "87032310",  # Автомобили с бензинов двигател
    "84713000",  # Portable digital automatic data processing machines
    "62034290",  # Men's or boys' trousers
    "85171200",  # Telephones for cellular networks
    "27101910",  # Petroleum oils
]

# Тестови 10-цифрени TARIC кодове
TEST_CODES_10_DIGIT = [
    "8703231000",  # Автомобили
    "8471300000",  # Лаптопи
    "6203420090",  # Мъжки панталони
    "8517120000",  # Мобилни телефони
    "2710191100",  # Дизелово гориво
]


def test_uk_api_xi(cn_code):
    """Тест на UK XI (Northern Ireland - EU aligned) API"""
    print(f"\n{'=' * 70}")
    print(f"🇪🇺 Testing UK XI (NI/EU aligned) API for CN code: {cn_code}")
    print(f"{'=' * 70}")

    # XI endpoint (Northern Ireland - EU tariffs)
    formatted_code = cn_code.ljust(10, '0') if len(cn_code) < 10 else cn_code[:10]
    url = f"https://www.trade-tariff.service.gov.uk/xi/api/v2/commodities/{formatted_code}"
    params = {'as_of': datetime.now().strftime('%Y-%m-%d')}
    headers = {
        'User-Agent': 'Odoo-BG-Tariff-Test/2.0',
        'Accept': 'application/vnd.uktt.v2+json'
    }

    try:
        start_time = time.time()
        response = requests.get(url, params=params, headers=headers, timeout=10)
        elapsed = time.time() - start_time

        print(f"⏱️  Response time: {elapsed:.2f}s")
        print(f"📊 Status code: {response.status_code}")
        print(f"🔗 URL: {url}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")

            # Извличане на description
            if 'data' in data and 'attributes' in data['data']:
                desc = data['data']['attributes'].get('description', 'N/A')
                print(f"📝 Description: {desc[:100]}...")

            # Извличане на duty rates
            if 'included' in data:
                measures_found = 0
                for item in data['included']:
                    if item.get('type') == 'measure':
                        attrs = item.get('attributes', {})
                        measure_type = attrs.get('measure_type_id', '')

                        if measure_type in ['103', '142', '105', '106']:
                            measures_found += 1
                            duty_expr = attrs.get('duty_expression', {})
                            base = duty_expr.get('base', 'N/A')
                            formatted = duty_expr.get('formatted_base', 'N/A')
                            print(f"\n💰 Measure Type {measure_type}:")
                            print(f"   Base: {base}")
                            print(f"   Formatted: {formatted}")

                if measures_found == 0:
                    print("⚠️  No Third Country duty measures found")
                else:
                    print(f"\n✅ Found {measures_found} relevant measures!")

            return True
        elif response.status_code == 404:
            print(f"❌ Not Found (404) - Code may not exist or is invalid")
            return False
        else:
            print(f"❌ Failed with status: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("⏰ Timeout after 10 seconds")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_uk_api_uk(cn_code):
    """Тест на UK (Great Britain) API"""
    print(f"\n{'=' * 70}")
    print(f"🇬🇧 Testing UK (GB) API for CN code: {cn_code}")
    print(f"{'=' * 70}")

    # UK endpoint (Great Britain tariffs)
    formatted_code = cn_code.ljust(10, '0') if len(cn_code) < 10 else cn_code[:10]
    url = f"https://www.trade-tariff.service.gov.uk/uk/api/v2/commodities/{formatted_code}"
    params = {'as_of': datetime.now().strftime('%Y-%m-%d')}
    headers = {
        'User-Agent': 'Odoo-BG-Tariff-Test/2.0',
        'Accept': 'application/vnd.uktt.v2+json'
    }

    try:
        start_time = time.time()
        response = requests.get(url, params=params, headers=headers, timeout=10)
        elapsed = time.time() - start_time

        print(f"⏱️  Response time: {elapsed:.2f}s")
        print(f"📊 Status code: {response.status_code}")
        print(f"🔗 URL: {url}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")

            # Извличане на description
            if 'data' in data and 'attributes' in data['data']:
                desc = data['data']['attributes'].get('description', 'N/A')
                print(f"📝 Description: {desc[:100]}...")

            # Извличане на duty rates
            if 'included' in data:
                measures_found = 0
                for item in data['included']:
                    if item.get('type') == 'measure':
                        attrs = item.get('attributes', {})
                        measure_type = attrs.get('measure_type_id', '')

                        if measure_type in ['103', '142', '105', '106']:
                            measures_found += 1
                            duty_expr = attrs.get('duty_expression', {})
                            base = duty_expr.get('base', 'N/A')
                            formatted = duty_expr.get('formatted_base', 'N/A')
                            print(f"\n💰 Measure Type {measure_type}:")
                            print(f"   Base: {base}")
                            print(f"   Formatted: {formatted}")

                if measures_found == 0:
                    print("⚠️  No Third Country duty measures found")
                else:
                    print(f"\n✅ Found {measures_found} relevant measures!")

            return True
        elif response.status_code == 404:
            print(f"❌ Not Found (404) - Code may not exist or is invalid")
            return False
        else:
            print(f"❌ Failed with status: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("⏰ Timeout after 10 seconds")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_all_codes():
    """Тества всички CN кодове"""
    print("\n" + "=" * 70)
    print("🚀 UK Trade Tariff API Testing Suite (UPDATED)")
    print("=" * 70)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {
        'xi': {'success': 0, 'failed': 0},
        'uk': {'success': 0, 'failed': 0}
    }

    print(f"\n{'=' * 70}")
    print("📋 Test Set 1: 8-digit CN codes (more reliable)")
    print(f"{'=' * 70}")

    for cn_code in TEST_CODES_8_DIGIT:
        # Test XI (Northern Ireland/EU)
        if test_uk_api_xi(cn_code):
            results['xi']['success'] += 1
        else:
            results['xi']['failed'] += 1

        time.sleep(0.5)  # Rate limiting

        # Test UK (Great Britain)
        if test_uk_api_uk(cn_code):
            results['uk']['success'] += 1
        else:
            results['uk']['failed'] += 1

        time.sleep(0.5)  # Rate limiting

    print(f"\n{'=' * 70}")
    print("📋 Test Set 2: 10-digit TARIC codes (may have issues)")
    print(f"{'=' * 70}")

    for cn_code in TEST_CODES_10_DIGIT[:2]:  # Test first 2 only
        # Test XI only
        if test_uk_api_xi(cn_code):
            results['xi']['success'] += 1
        else:
            results['xi']['failed'] += 1

        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    total_xi = results['xi']['success'] + results['xi']['failed']
    total_uk = results['uk']['success'] + results['uk']['failed']

    print("\n🇪🇺 UK XI (Northern Ireland/EU aligned) Results:")
    print(f"   ✅ Success: {results['xi']['success']}/{total_xi}")
    print(f"   ❌ Failed:  {results['xi']['failed']}/{total_xi}")

    print("\n🇬🇧 UK (Great Britain) API Results:")
    print(f"   ✅ Success: {results['uk']['success']}/{total_uk}")
    print(f"   ❌ Failed:  {results['uk']['failed']}/{total_uk}")

    # Recommendations
    print("\n💡 RECOMMENDATIONS:")

    if results['xi']['success'] > 0:
        print("   ✅ UK XI (NI/EU) API работи! Използвайте този endpoint за EU-aligned данни")

    if results['uk']['success'] > 0:
        print("   ✅ UK (GB) API работи! Подходящ за UK tariff данни")

    if results['xi']['success'] == 0 and results['uk']['success'] == 0:
        print("   ⚠️  Нито един API endpoint не връща данни")
        print("   📝 Възможни причини:")
        print("       - CN кодовете са невалидни или остарели")
        print("       - API-то изисква различен формат на кодовете")
        print("       - Network/firewall проблеми")
        print("\n   🔧 Решения:")
        print("       - Използвайте default rates за production")
        print("       - Изтеглете TARIC database локално от CIRCABC")
        print("       - Използвайте платен Taric Support API")


def test_single_code_detailed(cn_code):
    """Подробен тест на един CN код"""
    print("\n" + "=" * 70)
    print(f"🔬 DETAILED TEST for CN code: {cn_code}")
    print("=" * 70)

    test_uk_api_xi(cn_code)
    time.sleep(1)
    test_uk_api_uk(cn_code)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Test specific CN code
        cn_code = sys.argv[1]
        test_single_code_detailed(cn_code)
    else:
        # Test all predefined codes
        test_all_codes()

    print("\n✅ Testing completed!\n")
