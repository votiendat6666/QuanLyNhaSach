

//hàm thêm vào giỏ hàng
function addToCart(event, id, name, price) {
    event.preventDefault();
    fetch('/api/add-cart', {
        method: 'post',
        body: JSON.stringify({
            'id': id,
            'name': name,
            'price': price
        }),
        headers: {
            'Content-Type': 'application/json',
        }
    }).then(function(res) {
        console.info(res);
        return res.json();
    }).then(function(data) {
        console.info(data);

        let counter = document.getElementsByClassName('cart-counter')
        for(let i = 0; i < counter.length; i++) {
            counter[i].innerText = data.total_quantity;
        }
        counter.innerText = data.total_quantity;
    }).catch(function(error) {
        console.error('Error:', error);
    });
}



//hàm thanh toán và xóa sản phẩm trong giỏ hàng
function pay() {
    if (confirm('Bạn có chắc chắn muốn thanh toán giỏ hàng?') == true) {
        fetch('/api/pay', {
            method: 'post',
        }).then(res => {
            console.info('Response:', res);
            return res.json();
        }).then(data => {
            console.info('Data:', data);
            if (data.code == 200) {
                window.location.reload();
            } else {
                console.error('Failed to clear cart:', data.message);
            }
        }).catch(err => console.error('Error:', err));
    }
}

//hàm cập nhật giỏ hàng
function updateCart(id, object) {
    fetch('/api/update-cart', {
        method: 'put',
        body: JSON.stringify({
            'id': id,
            'quantity': parseInt(object.value)
        }),
        headers: {
            'Content-Type': 'application/json',
        }
    }).then(res => res.json()).then(data => {
        let counter = document.getElementsByClassName('cart-counter');
        for (let i = 0; i < counter.length; i++) {
            counter[i].innerText = data.total_quantity;
        }

        let amount = document.getElementById('total-amount');
        amount.innerText = new Intl.NumberFormat('vi-VN', { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(data.total_amount);

        // Update "Thành tiền" for the specific product
        let productTotal = document.getElementById('product-total-' + id);
        let productPrice = parseInt(document.getElementById('product-price-' + id).innerText.replace(/[^0-9]/g, ""));
        productTotal.innerText = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(productPrice * parseInt(object.value));
    });
}

//hàm xóa sản phẩm trong giỏ hàng
function deleteCart(id) {
    if (confirm("Bạn chắc chắn muốn xóa sản phẩm này không ??") == true){
    fetch('/api/delete-cart/' +id, {
        method: 'delete',
        headers: {
            'Content-Type': 'application/json',
        }
        }).then(res => res.json()). then(data => {
         let counter = document.getElementsByClassName('cart-counter')
        for(let i = 0; i < counter.length; i++) {
            counter[i].innerText = data.total_quantity;
        }
        let amount = document.getElementById('total-amount');
        amount.innerText = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(data.total_amount);
        let e = document.getElementById('product'+id)
        e.style.display = 'none';
        })
    }
    }



























