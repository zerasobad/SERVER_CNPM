from flask import render_template, url_for, redirect, request, session, jsonify, send_file, Response, flash
from server_app import app, db, dao, login, utils, admin, client, verify_sid
from flask_login import login_user, logout_user, login_required, current_user
from server_app.models import Role, HoaDon, NguoiDung, PhieuKham, QuyDinh
from datetime import datetime
import cloudinary
import cloudinary.uploader
import math

from server_app.utils import VnPayService

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    from fpdf import FPDF
    from PIL import Image
    import base64
    import io
    data = request.json
    image_data = data.get('image')

    # Tách phần header của Base64 và giải mã ảnh
    if image_data.startswith('data:image/png;base64,'):
        image_data = image_data.replace('data:image/png;base64,', '')
    image_bytes = base64.b64decode(image_data)

    # Lưu ảnh vào một đối tượng tạm thời
    image = Image.open(io.BytesIO(image_bytes))

    # Tạo file PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.image(image, x=10, y=10, w=190)  # Điều chỉnh kích thước và vị trí
    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    # Gửi file PDF về client
    return send_file(pdf_output, mimetype='application/pdf', as_attachment=True, download_name='chart.pdf')
@app.route("/")
def home_page():
    return render_template("home_page.html")

@app.route("/register", methods=['get', 'post'])
def user_register():
    err_msg = ""
    if request.method.__eq__('POST'):
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        try:
            if(password.strip().__eq__(confirm.strip())):
                dao.add_user(name=name, 
                             username=username, 
                             password=password)
                return redirect(url_for('user_login'))
            else:
                err_msg = 'Mật khẩu không khớp'
        except Exception as ex:
            err_msg = 'Hệ thống đang có lỗi' +str(ex)

    return render_template("register_page.html", 
                           err_msg=err_msg)

@app.route("/login", methods=['get', 'post'])
def user_login():
    err_msg = ''
    if request.method.__eq__('POST'):
        username = request.form.get('username')
        password = request.form.get('password')
        userRole = request.form.get('userRole')

        user = dao.check_login(username=username, 
                               password=password, 
                               userRole=userRole)

        if user:
            login_user(user=user) #current_user

            return redirect(url_for('home_page'))
        else:
            err_msg = 'Username hoặc password không chính xác'

    return render_template("login_page.html", 
                           err_msg=err_msg)

@app.route('/logout')
def user_signout():
    logout_user()
    return redirect(url_for('user_login'))

@login.user_loader
def user_load(user_id):
    return dao.get_user_by_id(user_id=user_id)

@app.context_processor
def common_responses():
    return {
        'medicine_state': utils.counter_medicine(session.get('medicine')),
        'Role': Role
    }

@app.route("/patient_information")
def patient_information():    
    return render_template("patient_infomation_page.html")

@app.route("/patient_information/<int:user_id>", methods=['get', 'post'])
def update_patient_infor(user_id):
    if request.method.__eq__('POST'):
        name = request.form.get('namebn')
        sex = request.form.get('sex')
        birth = request.form.get('birth')
        email = request.form.get('email')
        avatar = request.files.get('avatar')
        avatar_path = None
        if avatar:
                res = cloudinary.uploader.upload(avatar)
                avatar_path = res['secure_url']
        address = request.form.get('address')
        phone = request.form.get('phone')

        dao.update_patient(user_id=user_id, 
                           name=name, 
                           sex=sex, 
                           birth=birth, 
                           email=email, 
                           avatar=avatar_path, 
                           address=address, 
                           phone=phone)
        return redirect(url_for('home_page'))

@app.route('/register_medical', methods=['get', 'post'])
def medical_register():
    msg = ''
    if not current_user.is_authenticated:
        return redirect('/login')
    elif current_user.loaiNguoiDung == Role.Patient: 
        if request.method.__eq__('POST'):
            date = request.form.get('date')
            time = request.form.get('time')

            date_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
            count = dao.count_register_medical(date = date)
            quyDinh = dao.lay_so_luong('Mỗi ngày khám tối đa 40 bệnh nhân')
            print("debug register medical")
            print(count)
            print(quyDinh)
            if count >= 0 and count < quyDinh:
                dao.register_medical(patient_id=current_user.id,
                                     date_time=date_time)
                pass
            else: 
                msg = 'Đã đủ số lượng đăng ký'

            if not msg:
                return redirect(url_for('home_page'))
            
    elif current_user.loaiNguoiDung == Role.Nurse:
        if request.method.__eq__('POST'):
            phone = request.form.get('phone')
            date = request.form.get('date')
            time = request.form.get('time')

            date_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
            count = dao.count_register_medical(date = date)
            quyDinh = dao.lay_so_luong('Mỗi ngày khám tối đa 40 bệnh nhân')
            print("count:" + str(count));
            print("quyDinh:" + str(quyDinh));
            if count >= 0 and count < quyDinh:
                dao.register_medical(phone=phone,
                                     date_time=date_time,
                                     nurse_id=current_user.id)
            else:
                msg = 'Đã đủ số lượng đăng ký'

            if not msg:
                return redirect(url_for('home_page'))
    return render_template('medical_register_page.html', 
                           msg=msg)
    
@app.route("/medical_list", methods=['get'])
def medical_list():
    date = request.args.get('date')
    medical_list = dao.get_register_medical_by_date(date=date)

    return render_template('medical_examination_list_page.html', 
                           medical_list=medical_list)

# @app.route('/generate_pdf/<date>', methods=['GET'])
# def generate_pdf(date):
#     # date = request.args.get('date')
#     print(f"date ne 123: {date}")
#
#     medical_list = dao.get_register_medical_by_date(date=date)
#     pdf = dao.create_medical_list_pdf(medical_list)
#     pdf.seek(0)  # Đảm bảo con trỏ ở đầu tệp
#
#     return send_file(
#         pdf,
#         download_name='medical_list.pdf',  # Sửa 'attachment_filename' thành 'download_name'
#         as_attachment=True,
#         mimetype='application/pdf'  # Thiết lập mimetype cho header
#     )


@app.route("/medicine")
def drugs_list():
    kw = request.args.get("keywordthuoc")
    counter = dao.count_medicine()
    page = request.args.get("page", 1)
    drugs = dao.load_medicine(kw=kw, page=int(page))
    return render_template('medicine.html',
                           drugs=drugs,
                           pages=math.ceil(counter / app.config['PAGE_SIZE']))

@app.route('/login_admin',methods=['post', 'get'])
def login_admin():
    if request.method.__eq__('POST'):
        username = request.form.get('usernameAd')
        password = request.form.get('passwordAd')

        user = dao.check_login(username=username, 
                               password=password,
                               userRole=Role.Admin)

        if user:
            login_user(user=user)

    return redirect('/admin')

#===========================================================
@app.route('/examination_form', methods=['get', 'post'])
def create_examination_form():
    if request.method == 'POST':
        name = request.form.get('name')
        date = request.form.get('date')
        symptom = request.form.get('symptom')
        disease = request.form.get('disease')
        medicineName = request.form.get('medicineName')
        quantity = request.form.get('quantity')
        unit = request.form.get('unit')
        instruction = request.form.get('instruction')

        # Gọi hàm add_examination_form và kiểm tra kết quả
        success = dao.add_examination_form(
            name=name,
            date=date,
            symptom=symptom,
            disease=disease,
            medicineName=medicineName,
            quantity=quantity,
            unit=unit,
            instruction=instruction,
            id=current_user.id
        )

        if not success:
            # Nếu thất bại, dừng và hiển thị thông báo lỗi
            return render_template('examination_form.html')

        # Nếu thành công, thông báo thành công
        flash('Đã tạo phiếu khám thành công!', 'success')

    return render_template('examination_form.html')


@app.route("/patient_search")
def patient_list():
    kw = request.args.get("keywordPatient")
    counter = dao.count_patient()
    page = request.args.get("page", 1)
    patients = dao.load_patient(kw=kw, page=int(page))
    return render_template('search_patient.html',
                           patients=patients,
                           pages=math.ceil(counter / app.config['PAGE_SIZE']))

@app.route('/api/save_exam_data', methods=['POST'])
def save_exam_data():
    data = request.json 
    session['exam_data'] = data  
    return jsonify({'message': 'Exam data saved successfully'})

@app.route('/api/get_exam_data', methods=['GET'])
def get_exam_data():
    exam_data = session.get('exam_data', {})
    print(exam_data)
    return jsonify(exam_data)




@app.route('/receipt', methods=['GET'])
def receipt():
    # Lấy danh sách tất cả các phiếu khám từ cơ sở dữ liệu
    list_examination = dao.get_list_examination()

    return render_template('receipt.html', list_examination=list_examination)




@app.route('/generate_invoice_pdf/<int:hoa_don_id>', methods=['GET'])
def generate_invoice_pdf(hoa_don_id):
    # Lấy thông tin hóa đơn từ database
    print("ccccccccccccccccccc")
    hoa_don = db.session.query(HoaDon).filter_by(id=hoa_don_id).first()
    nguoi_dung = db.session.query(NguoiDung).filter_by(id=hoa_don.thuNgan_id).first()
    phieu_kham = db.session.query(PhieuKham).filter_by(id=hoa_don.phieuKham_id).first()

    if not hoa_don or not nguoi_dung or not phieu_kham:
        return "Không tìm thấy hóa đơn", 404

    # Tạo danh sách dữ liệu để gửi vào hàm tạo PDF
    medical_list = [{
        'hoa_don_id': hoa_don.id,
        'thu_ngan': nguoi_dung.hoTen,
        'ngay_lap': hoa_don.ngayLap.strftime('%d-%m-%Y'),
        'phieu_kham_id': hoa_don.phieuKham_id,
        'tien_kham': hoa_don.tienKham,
        'tien_thuoc': hoa_don.tienThuoc,
        'tong_tien': hoa_don.tongTien,
        'so_dien_thoai': phieu_kham.benhNhan.soDienThoai,
    }]

    # Sử dụng hàm tạo PDF hiện có
    pdf = dao.create_invoice_pdf(medical_list)
    pdf.seek(0)

    return send_file(
        pdf,
        download_name=f'invoice_{hoa_don.id}.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )

@app.route('/payment_history', methods=['GET'])
def payment_history():
    search_kw = request.args.get('search_kw', '')

    # Lọc các hóa đơn đã thanh toán (dựa trên các cột tienKham, tienThuoc, tongTien)
    query = db.session.query(HoaDon, NguoiDung, PhieuKham).join(NguoiDung, HoaDon.thuNgan_id == NguoiDung.id).join(PhieuKham, HoaDon.phieuKham_id == PhieuKham.id)

    # Nếu có từ khóa tìm kiếm
    if search_kw:
        query = query.filter(
            (PhieuKham.benhNhan.hoTen.like(f'%{search_kw}%') | HoaDon.ngayLap.like(f'%{search_kw}%'))
        )

    # Lọc theo điều kiện hóa đơn đã thanh toán (giả sử có giá trị tiền khám, tiền thuốc, tổng tiền)
    data = query.filter(
        HoaDon.tienKham > 0,
        HoaDon.tienThuoc > 0,
        HoaDon.tongTien > 0
    ).all()
    print("data nee:" + str(data))
    for hoa_don, nguoi_dung, phieu_kham in data:
        print(
            f"HoaDon ID: {hoa_don.id}, Ngay Lap: {hoa_don.ngayLap}, Tien Kham: {hoa_don.tienKham}, Tien Thuoc: {hoa_don.tienThuoc}, Tong Tien: {hoa_don.tongTien}")
        print(f"Nguoi Dung ID: {nguoi_dung.id}, Ho Ten: {nguoi_dung.hoTen}")
        print(
            f"Phieu Kham ID: {phieu_kham.id}, Ngay Kham: {phieu_kham.ngayKham}, Benh Nhan: {phieu_kham.benhNhan.diaChi}")

    return render_template('payment_history.html', hoa_dons=data)


# Khởi tạo VNPayService
vn_pay_service = VnPayService()

# @app.route('/api/pay', methods=['post'])
# def pay():
#     data = request.json
#     print("data" + str(data))
#     id = str(data.get('phieuKhamId'))
#     print("iddđ" + id)
#     print("current_user.id" + str(current_user.id))
#     try:
#         dao.create_receipt(phieuKham_id=id,
#                        thuNgan_id=current_user.id)
#     except:
#         return jsonify({'code': 400})
#
#     return jsonify({'code': 200})

# Sau khi thanh toán, xử lý kết quả trả về từ VNPay
@app.route('/payment-return', methods=['GET'])
def payment_return():
    try:
        # Lấy các tham số trả về từ VNPay
        query_parameters = request.args.to_dict()

        # Xử lý kết quả thanh toán từ VNPay
        result = vn_pay_service.payment_execute(query_parameters)

        if result['success']:
            return jsonify({
                "success": True,
                "message": "Payment successful",
                "data": result
            })
        else:
            return jsonify({"success": False, "message": "Invalid signature or payment failed"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/receipt/<int:phieuKhamId>', methods=['POST'])
def create_receipt_for_examination(phieuKhamId):
    try:
        # Lấy dữ liệu từ request (phieuKhamId được truyền qua URL)
        data = request.json
        total_amount = data.get('total_amount', 0)  # Lấy total_amount từ body

        print(f"Received phieuKhamId: {phieuKhamId}, total_amount: {total_amount}")

        session['phieuKhamId'] = phieuKhamId

        # Gọi VNPay service để tạo URL thanh toán
        payment_url = vn_pay_service.create_payment_url(total_amount)

        print("payment_url", payment_url)

        # Trả về URL thanh toán trong JSON
        return jsonify({'code': 200, 'payment_url': payment_url})
    except Exception as e:
        # Nếu có lỗi, trả về mã lỗi
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/payment-success', methods=['GET'])
def payment_success():
    # Lấy phieuKhamId từ session
    phieuKhamId = session.get('phieuKhamId')

    # Kiểm tra nếu phieuKhamId có giá trị hợp lệ
    if phieuKhamId:
        try:
            # Chuyển phieuKhamId về kiểu int trước khi truyền vào dao.create_receipt
            phieuKhamId = int(phieuKhamId)

            # Tạo hóa đơn với phieuKhamId và thuNgan_id
            dao.create_receipt(phieuKham_id=phieuKhamId, thuNgan_id=current_user.id)

            session.pop('phieuKhamId', None)  # Xóa phieuKhamId khỏi session

            # Trả về giao diện thanh toán thành công
            return render_template('payment_success.html')
        except ValueError:
            # Nếu không thể chuyển đổi phieuKhamId thành int, trả về lỗi
            return jsonify({'code': 400, 'message': 'Invalid phieuKhamId'}), 400
    else:
        # Nếu không có phieuKhamId trong session, trả về lỗi
        return jsonify({'code': 400, 'message': 'phieuKhamId is missing in session'}), 400


if __name__ == '__main__':
    app.run(debug=True)