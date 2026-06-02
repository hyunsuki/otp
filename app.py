import streamlit as st
import cv2
import numpy as np
import base64
from urllib.parse import urlparse, parse_qs
# PC 앱 폴더에 있던 protobuf 컴파일 파일을 임포트합니다.
import migration_pb2 as pb2 

st.set_page_config(page_title="내부망 OTP 키 추출기", page_icon="🔐", layout="centered")
st.title("🔐 내부망 OTP 시크릿 키 추출기")

uploaded_file = st.file_uploader("QR 코드 이미지 업로드", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if img is not None:
        detector = cv2.QRCodeDetector()
        qr_data, _, _ = detector.detectAndDecode(img)
        
        if qr_data:
            # 💡 구글 OTP 내보내기용 대형 QR 데이터 처리부
            if "otpauth-migration://" in qr_data:
                st.success("✅ 구글 OTP 내보내기 데이터 감지 성공!")
                try:
                    parsed = urlparse(qr_data)
                    data = parse_qs(parsed.query)["data"][0]
                    padded = data + "=" * (-len(data) % 4)
                    binary = base64.urlsafe_b64decode(padded)
                    
                    # 프로토콜 버퍼 역직렬화 (해체 작업)
                    payload = pb2.MigrationPayload()
                    payload.ParseFromString(binary)
                    
                    st.subheader("📋 포함된 OTP 계정 리스트")
                    # 긴 데이터 내부에 숨겨진 진짜 개별 시크릿 키들을 모두 추출합니다.
                    for idx, param in enumerate(payload.otp_parameters):
                        # 바이너리 형태의 키를 표준 Base32 텍스트 키로 변환
                        real_secret = base64.b32encode(param.secret).decode()
                        
                        st.write(f"**계정 {idx+1}: {param.name}** ({param.issuer if param.issuer else '알 수 없음'})")
                        # 이 키를 복사해서 PC 프로그램에 넣으면 됩니다!
                        st.code(real_secret, language="text") 
                        
                except Exception as e:
                    st.error(f"구글 OTP 내보내기 데이터 해독 실패: {str(e)}")
                    st.info("힌트: migration_pb2.py 파일이 같은 폴더에 있어야 합니다.")
            
            # 일반 표준 OTP 주소 처리부
            elif "otpauth://" in qr_data:
                parsed = urlparse(qr_data)
                secret = parse_qs(parsed.query).get("secret", [None])[0]
                if secret:
                    st.success("✅ 일반 OTP 시크릿 키 추출 성공!")
                    st.code(secret, language="text")
