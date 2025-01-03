import json
import os.path
from server_app import app ,db
from server_app.models  import Thuoc ,Role, NguoiDung, ToaThuoc, PhieuKham,HoaDon
from flask_login import current_user
import hashlib
from sqlalchemy import func

def counter_medicine(medicine):
    total_quantity,total_price = 0,0
    if medicine:
        for c in medicine.values():
            total_quantity += c['quantity']
            total_price += c['quantity']*c['donGia']
            
    return {
        'total_quantity': total_quantity,
        'total_price': total_price
        }


def add_receipt(medicine):
    if medicine:
        receipt = PhieuKham(user=current_user)
        a="3 lan"
        b = "3 lan"
        db.session.add(receipt)
        for c in medicine.values():
            d =ToaThuoc(receipt=receipt,medicine_id=c['id'],soLuong=c['quantity'],lieuLuong=a,cachDung=b)
            db.session.add(d)
        db.session.commit()




def sales_report():
    # Lấy chỉ một số cột cụ thể
    specific_columns = HoaDon.query.with_entities(HoaDon.id, HoaDon.tienKham, HoaDon.tienThuoc,HoaDon.tongTien,HoaDon.ngayLap,HoaDon.thuNgan_id,HoaDon.phieuKham_id).all()
    return  specific_columns
    # return HoaDon.query.all()
    # monthly_data = {}
    # for invoice in invoices:
    #     month_year = invoice.ngayLap.strftime('%Y-%m')
    #     if month_year not in monthly_data:
    #         monthly_data[month_year] = {'total_amount': 0, 'visit_count': 0}
    #     monthly_data[month_year]['total_amount'] += invoice.amount
    #     monthly_data[month_year]['visit_count'] += 1
    # return monthly_data

def total_amount_by_month():
    result = db.session.query(
        func.CONCAT(func.YEAR(HoaDon.ngayLap), '-', func.FORMAT(func.MONTH(HoaDon.ngayLap), '00')).label('thang_nam'),
        func.sum(HoaDon.tongTien).label('Tong tien')
    ).group_by(func.CONCAT(func.YEAR(HoaDon.ngayLap), '-', func.FORMAT(func.MONTH(HoaDon.ngayLap), '00'))).all()

    # Chuyển kết quả thành danh sách từ điển để trả về JSON hoặc sử dụng trong template
    return result

#  vnpay lib
import hmac
import hashlib
import urllib.parse

class VnPayLibrary:
    def __init__(self):
        self._request_data = {}
        self._response_data = {}

    def add_request_data(self, key, value):
        if value:
            self._request_data[key] = value

    def add_response_data(self, key, value):
        if value:
            self._response_data[key] = value

    def get_response_data(self, key):
        return self._response_data.get(key, '')

    # Create request URL
    def create_request_url(self, base_url, vnp_hash_secret):
        query_string = "&".join(
            f"{urllib.parse.quote_plus(key)}={urllib.parse.quote_plus(value)}"
            for key, value in sorted(self._request_data.items()) if value
        )

        base_url += "?" + query_string
        sign_data = query_string

        # Generate HMAC SHA512 hash
        vnp_secure_hash = Utils.hmac_sha512(vnp_hash_secret, sign_data)
        base_url += "&vnp_SecureHash=" + vnp_secure_hash

        return base_url

    # Validate the signature
    def validate_signature(self, input_hash, secret_key):
        rsp_raw = self.get_response_data_string()
        my_checksum = Utils.hmac_sha512(secret_key, rsp_raw)
        return my_checksum.lower() == input_hash.lower()

    # Helper method to generate response data string
    def get_response_data_string(self):
        filtered_response = {
            key: value for key, value in self._response_data.items()
            if key not in ["vnp_SecureHashType", "vnp_SecureHash"]
        }
        query_string = "&".join(
            f"{urllib.parse.quote_plus(key)}={urllib.parse.quote_plus(value)}"
            for key, value in sorted(filtered_response.items()) if value
        )
        return query_string


class Utils:
    @staticmethod
    def hmac_sha512(key, input_data):
        key_bytes = key.encode('utf-8')
        input_bytes = input_data.encode('utf-8')
        hmac_hash = hmac.new(key_bytes, input_bytes, hashlib.sha512).hexdigest()
        return hmac_hash

    @staticmethod
    def get_ip_address(request):
        try:
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip_address and ',' in ip_address:
                ip_address = ip_address.split(',')[0]
            return ip_address
        except Exception as e:
            return f"Invalid IP: {str(e)}"

    # service vnpay

from flask import request, current_app
from datetime import datetime
import hashlib
import hmac
import os
from urllib.parse import urlencode, parse_qs

class VnPayService:
    def __init__(self):
        self.config = {
            "Version": os.getenv("VNP_VERSION", "2.1.0"),
            "Command": os.getenv("VNP_COMMAND", "pay"),
            "TmnCode": os.getenv("VNP_TMNCODE", "NJJ0R8FS"),
            "CurrCode": os.getenv("VNP_CURRCODE", "VND"),
            "Locale": os.getenv("VNP_LOCALE", "vn"),
            "PaymentBackReturnUrl": os.getenv("VNP_RETURN_URL", "http://127.0.0.1:5000/payment-success"),
            "BaseUrl": os.getenv("VNP_BASE_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"),
            "HashSecret": os.getenv("VNP_HASH_SECRET", "BYKJBHPPZKQMKBIBGGXIYKWYFAYSJXCW")
        }

    def create_payment_url(self, total_amount):
        total_amount = float(total_amount)

        tick = str(int(datetime.utcnow().timestamp() * 1000))

        vnp = VnPayLibrary()
        vnp.add_request_data("vnp_Version", self.config["Version"])
        vnp.add_request_data("vnp_Command", self.config["Command"])
        vnp.add_request_data("vnp_TmnCode", self.config["TmnCode"])
        vnp.add_request_data("vnp_Amount", str(int(total_amount) * 100))
        vnp.add_request_data("vnp_CreateDate", datetime.now().strftime("%Y%m%d%H%M%S"))
        vnp.add_request_data("vnp_CurrCode", self.config["CurrCode"])
        vnp.add_request_data("vnp_IpAddr", request.remote_addr)
        vnp.add_request_data("vnp_Locale", self.config["Locale"])
        vnp.add_request_data("vnp_OrderInfo", "Thanh toán đơn hàng với VNPay")
        vnp.add_request_data("vnp_OrderType", "other")
        vnp.add_request_data("vnp_ReturnUrl", self.config["PaymentBackReturnUrl"])
        vnp.add_request_data("vnp_TxnRef", tick)

        payment_url = vnp.create_request_url(self.config["BaseUrl"], self.config["HashSecret"])
        return payment_url

    def payment_execute(self, query_parameters):
        vnp = VnPayLibrary()
        for key, value in query_parameters.items():
            if key.startswith("vnp_"):
                vnp.add_response_data(key, value)

        vnp_order_id = vnp.get_response_data("vnp_TxnRef")
        vnp_transaction_id = vnp.get_response_data("vnp_TransactionNo")
        vnp_secure_hash = query_parameters.get("vnp_SecureHash", "")
        vnp_response_code = vnp.get_response_data("vnp_ResponseCode")
        vnp_order_info = vnp.get_response_data("vnp_OrderInfo")

        check_signature = vnp.validate_signature(vnp_secure_hash, self.config["HashSecret"])
        if not check_signature:
            return {
                "success": False
            }

        return {
            "success": True,
            "payment_method": "VnPay",
            "order_description": vnp_order_info,
            "order_id": vnp_order_id,
            "transaction_id": vnp_transaction_id,
            "token": vnp_secure_hash,
            "vn_pay_response_code": vnp_response_code
        }
