import streamlit as st
import cv2
import numpy as np
import base64
import os
import sys
from urllib.parse import urlparse, parse_qs
from google.protobuf.message import DecodeError


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
sys.path.append(CURRENT_DIR)


import migration_pb2 as pb2

# 페이지 기본 설정
st.set_page_config(page_title="내부망 OTP 키 추출기", page_icon="🔐", layout="centered")

st.title("🔐 내부망 OTP 시크릿 키 추출기")
st.caption("스마트폰으로 QR 코드를 업로드하여 PC 프로그램에 입력할 시크릿 키를 추출하세요.")

# 파일 업로더 컴포넌트
uploaded_file = st.file_uploader("QR 코드 이미지 업로드 (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg", "PNG"])

if uploaded_file is not None:
    try:
        # 1. 파일 시스템 잠금 우회 및 바이너리 데이터를 OpenCV 행렬로 디코딩
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is None:
            st.error("이미지를 로드할 수 없습니다. 깨진 파일이거나 지원하지 않는 포맷입니다.")
        else:
            # 2. QR 코드 인식 디텍터 가동
            detector = cv2.QRCodeDetector()
            qr_data, _, _ = detector.detectAndDecode(img)
            
            # 저화질/RDP 환경 대응용 2차 정밀 디텍터 백업
            if not qr_data:
                try:
                    obj = cv2.QRCodeDetector()
                    qr_data_multi, _, _, _ = obj.detectAndDecodeMulti(img)
                    if qr_data_multi and isinstance(qr_data_multi, list):
                        qr_data = qr_data_multi[0]
                except:
                    pass

            if not qr_data or not str(qr_data).strip():
                st.error("이미지에서 QR 코드를 인식하지 못했습니다. QR 코드가 선명하게 보이도록 다시 캡처해 주세요.")
            else:
                qr_data = str(qr_data).strip()
                st.subheader("📋 인식 결과")
                
                # =====================================================
                # [방식 A] Google OTP Export QR (원본 프로젝트 정밀 로직)
                # =====================================================
                if "otpauth-migration://" in qr_data:
                    st.info("Google OTP 내보내기용 QR 코드가 감지되었습니다.")
                    try:
                        parsed = urlparse(qr_data)
                        data = parse_qs(parsed.query)["data"][0]
                        padded = data + "=" * (-len(data) % 4)
                        binary = base64.urlsafe_b64decode(padded)
                        
                        # 💡 기존 소스 코드와 완전히 동일한 Protobuf 파싱 구조
                        payload = pb2.MigrationPayload()
                        payload.ParseFromString(binary)
                        
                        if not payload.otp_parameters:
                            st.error("내부 프로토콜 버퍼에 OTP 데이터가 존재하지 않습니다.")
                        else:
                            st.success("✅ 시크릿 키 추출 성공!")
                            st.write("아래의 키를 복사하여 내부망 PC 프로그램에 직접 입력하세요:")
                            
                            # 내부에 묶여 있는 다중 계정을 원본 규칙대로 순회 및 Base32 변환
                            for idx, param in enumerate(payload.otp_parameters):
                                real_secret = base64.b32encode(param.secret).decode()
                                account_name = param.name if param.name else f"계정 {idx+1}"
                                issuer_name = f" ({param.issuer})" if param.issuer else ""
                                
                                # 사용자가 쉽게 복사할 수 있도록 각각 코드 블록으로 래핑 출력
                                st.write(f"**📌 {account_name}{issuer_name}**")
                                st.code(real_secret, language="text")
                                
                    except DecodeError:
                        st.error("Google OTP QR 프로토콜 버퍼 데이터 해독에 실패했습니다.")
                    except Exception as e:
                        st.error(f"데이터 추출 중 예외 발생: {str(e)}")
                        
                # =====================================================
                # [방식 B] 일반 표준 개별 otpauth QR
                # =====================================================
                elif "otpauth://" in qr_data:
                    parsed = urlparse(qr_data)
                    secret = parse_qs(parsed.query).get("secret", [None])[0]
                    if secret:
                        st.success("✅ 일반 단일 OTP 시크릿 키 추출 성공!")
                        st.write("아래의 키를 복사하여 내부망 PC 프로그램에 직접 입력하세요:")
                        st.code(secret.upper(), language="text")
                    else:
                        st.error("QR 주소 규격은 맞으나 내부에 secret(시크릿 키) 인자가 누락되었습니다.")
                else:
                    st.warning("지원되지 않는 일반 텍스트 주소 형식입니다:")
                    st.code(qr_data, language="text")
                    
    except Exception as e:
        st.error(f"웹 애플리케이션 실행 오류: {str(e)}")
