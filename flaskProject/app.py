from flask import Flask, Response, jsonify, request,render_template
from utils.cameraClass import VideoCamera
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import threading
from utils.databaseClass import MySQLDatabase

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'rbcc'
app.config['MYSQL_CHARSET'] = 'utf8mb4'

camera = None  # 全局摄像头实例
camera_lock = threading.Lock()  # 全局锁控制摄像头实例的创建/释放
db = MySQLDatabase(app)


#摄像头输送帧
def generate_frames():
    global camera
    try:
        with camera_lock:
            if camera is None:
                camera = VideoCamera()  # 默认使用摄像头0
        while True:
            with camera_lock:
                if camera is None:
                    break
                frame = camera.get_frame()
            if frame is None:
                break
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
    finally:
        if camera is not None:
            camera.release()

@app.route('/')
def index():
    return render_template('index.html')
    # return render_template('management.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control_camera', methods=['POST'])
def control_camera():
    global camera
    action = request.json.get('action')
    camera_id = request.json.get('camera_id', 0)  # 默认为0号摄像头

    with camera_lock:
        if action == 'open':
            if camera is not None:
                camera.release()
            camera = VideoCamera(camera_id)
            return jsonify({"status": "success", "message": f"摄像头{camera_id}已开启"})
        elif action == 'close' and camera is not None:
            camera.release()
            camera = None
            return jsonify({"status": "success", "message": "摄像头已关闭"})
    return jsonify({"status": "error", "message": "无效操作"}), 400


@app.route('/equipment_archive/insert', methods=['POST'])  # 明确指定POST方法
def insert_into_equiment_archive():
    try:
        # 获取前端发送的JSON数据
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "未接收到数据"}), 400

        # 提取字段并验证必填项
        required_fields = ['equipment_id', 'model', 'location', 'supplier']
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "缺少必填字段"}), 400

        # 处理生产日期（前端未传则用当前日期）
        production_date = data.get('production_date') or datetime.now().strftime('%Y-%m-%d')

        # 执行数据库插入
        sql = """
        INSERT INTO Equipment_Archive 
        (equipment_id, model, location, supplier, production_date) 
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            data['equipment_id'],
            data['model'],
            data['location'],
            data['supplier'],
            production_date
        )
        result = db.insert(sql, params)

        return jsonify({
            "status": "success",
            "message": f"插入了 {result} 条记录",
            "data": data  # 可选：返回插入的数据供前端确认
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/equipment_archive/delete', methods=['POST'])  # 明确指定POST方法
def delete_from_equipment_archive():
    try:
        # 获取前端发送的JSON数据
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "未接收到数据"}), 400

        # 验证必填字段
        if 'equipment_id' not in data:
            return jsonify({"status": "error", "message": "缺少设备ID字段"}), 400

        equipment_id = data['equipment_id']

        # 检查设备是否存在（可选步骤，避免无效操作）
        check_sql = "SELECT equipment_id FROM Equipment_Archive WHERE equipment_id = %s"
        existing = db.query_one(check_sql, (equipment_id,))
        if not existing:
            return jsonify({"status": "error", "message": f"设备ID {equipment_id} 不存在"}), 404

        # 执行级联删除（依赖数据库外键约束）
        delete_sql = "DELETE FROM Equipment_Archive WHERE equipment_id = %s"
        result = db.delete(delete_sql, (equipment_id,))

        # 返回操作结果
        return jsonify({
            "status": "success",
            "message": f"删除了 {result} 条设备记录及其关联数据",
            "deleted_id": equipment_id
        })

    except Exception as e:
        # 捕获数据库错误（如外键约束冲突）
        return jsonify({
            "status": "error",
            "message": f"删除失败: {str(e)}",
            "hint": "请检查是否有未处理的关联数据或数据库连接问题"
        }), 500


@app.route('/camera/bind', methods=['POST'])
def bind_camera_to_equipment():
    """
    覆盖式绑定摄像头到设备
    ---
    如果设备已有绑定记录，则先删除旧记录再插入新绑定
    """
    try:
        data = request.get_json()

        # 验证必填字段
        required_fields = ['equipment_id', 'camera_id', 'flash_required']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "status": "error",
                "message": f"缺少必填字段: {', '.join(missing_fields)}"
            }), 400

        # 检查设备是否存在
        equipment = db.query_one(
            "SELECT equipment_id FROM Equipment_Archive WHERE equipment_id = %s",
            (data['equipment_id'],)
        )
        if not equipment:
            return jsonify({
                "status": "error",
                "message": "设备不存在"
            }), 400

        # 检查是否已绑定其他摄像头
        existing_binding = db.query_one(
            "SELECT * FROM Camera_Definition WHERE equipment_id = %s",
            (data['equipment_id'],)
        )

        # 如果已有绑定，先删除旧记录
        if existing_binding:
            delete_result = db.delete(
                "DELETE FROM Camera_Definition WHERE equipment_id = %s",
                (data['equipment_id'],)
            )
            if delete_result == 0:
                return jsonify({
                    "status": "error",
                    "message": "删除旧绑定记录失败"
                }), 500

        # 执行新绑定
        result = db.insert(
            "INSERT INTO Camera_Definition (equipment_id, camera_id, flash_required) VALUES (%s, %s, %s)",
            (data['equipment_id'], data['camera_id'], data['flash_required'])
        )

        if result == 1:
            return jsonify({
                "status": "success",
                "message": "绑定成功",
                "data": data
            })
        else:
            return jsonify({
                "status": "error",
                "message": "绑定失败"
            }), 500

    except Exception as e:
        current_app.logger.error(f"绑定摄像头失败: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"绑定失败: {str(e)}"
        }), 500

@app.route('/test/cambind')
def cambind():
    return render_template('cam_bind.html')

@app.route('/test/delete')
def equi_del():
    return (render_template('equipment_delete.html'))

@app.route('/test/add')
def equi_add():
    return (render_template('management.html'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
