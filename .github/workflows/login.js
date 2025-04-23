

// 登入函式
async function login() {
    const name = document.getElementById('name').value;
    const phone = document.getElementById('phone').value;
    const inputPassword = document.getElementById('password').value;

    try {
        const snapshot = await db.collection('members').where('phone', '==', phone).get();

        if (snapshot.empty) {
            document.getElementById('status').innerText = '找不到此會員！';
            return;
        }

        const doc = snapshot.docs[0];
        const data = doc.data();
        const savedHash = data.password_hash;

        const match = await bcrypt.compare(inputPassword, savedHash);

        if (match) {
            document.getElementById('status').innerText = `登入成功！歡迎 ${data.name}`;
            // 可以導向會員中心
            // window.location.href = "/member.html";
        } else {
            document.getElementById('status').innerText = '密碼錯誤';
        }

    } catch (err) {
        console.error(err);
        document.getElementById('status').innerText = '登入時發生錯誤';
    }
}
