import React, { useState, useEffect, useRef, useContext } from 'react';
import { UserContext } from './UserContext';
import './Chat.css';

const selectedProductsMap = {};

const Chat = ({ socketOpen, sendMessage, socket }) => {
  const { user, userId } = useContext(UserContext);
  // console.log("user", user)
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState('');
  const [currentConfirmMessage, setCurrentConfirmMessage] = useState(null);
  const [currentToolCallId, setCurrentToolCallId] = useState(null);
  const [selectedOrderId, setSelectedOrderId] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  
  const chatRef = useRef(null);

  useEffect(() => {
    if (socket) {
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (!data.datetime) {
          data.datetime = new Date().toISOString();
        }
        if (data.message) {
          setMessages((prevMessages) => [...prevMessages, data]);
        }
        
        if (data.products) {
          displayProductList(data.products);
        }
        if (data.fetched_orders) {
          console.log("data.fetched_orders: ", data.fetched_orders);
          displayFetchedOrders(data.fetched_orders, chatRef.current);
        }
        if (data.changeable_orders) {
          console.log("data.changeable_orders: ", data.changeable_orders);
          const orderChangeType = data.order_change_type;
          displayFetchedOrders(data.changeable_orders, chatRef.current, orderChangeType);
        }
        if (typeof data.confirm_message !== 'undefined' && data.confirm_message !== null) {
          console.log("confirm_message 존재!", data.confirm_message)
          console.log("confirm_message 존재!", data)
          
          setCurrentConfirmMessage(data.confirm_message);
          setCurrentToolCallId(data.tool_call_id);
        }

        
      };
    }
  }, [socket]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!socketOpen) {
      console.error('WebSocket connection not established or closed.');
      return;
    }

    if (message.trim()) {
      const newMessage = {
        userId: userId || 'Anonymous',
        message,
        datetime: new Date().toISOString(),
      };
      console.log("currentConfirmMessage, currentToolCallId", currentConfirmMessage, )

      if (selectedOrderId) {
        newMessage.orderId = selectedOrderId;
      }
      if (currentConfirmMessage) {
        newMessage.confirmMessage = currentConfirmMessage;
      }
      if (currentToolCallId) {
        newMessage.toolCallId = currentToolCallId;
      }
      
      console.log("전송 데이터\n", newMessage);
      setMessages((prevMessages) => [...prevMessages, newMessage]);
      sendMessage(newMessage);
      setMessage('');

      setCurrentConfirmMessage(null);
      setCurrentToolCallId(null);
      setSelectedOrderId(null); 
      setSelectedOrder(null);
      console.log("할당값 초기화\n", selectedOrderId, currentConfirmMessage, currentToolCallId);
    } else {
      console.error('Message cannot be empty.');
    }
  };

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const displayProductList = (products, orderId = null) => {
    const uniqueContainerId = `selected-products-container-${Date.now()}`;
    selectedProductsMap[uniqueContainerId] = {};

    const productListHtml = `
      <div class="message other">
        <strong>메뉴 목록</strong><br>
        <ul class="list-group">
          ${products.map((product, index) => `
            <li class="list-group-item">
              <div class="d-flex justify-content-between align-items-center">
                <span><strong>${product.product_name}</strong> - ${product.price}원</span>
                <input type="number" id="product-quantity-${uniqueContainerId}-${index}" class="form-control product-quantity" style="width: 70px;" min="1" value="1" data-product-id="${index}">
                <button class="btn btn-primary btn-sm select-button" data-product-id="${index}" data-product-name="${product.product_name}" data-product-price="${product.price}">선택</button>
              </div>
            </li>`).join('')}
        </ul>
      </div>
      <div id="${uniqueContainerId}">
        <h5>선택된 상품</h5>
        <ul id="selected-products-list-${uniqueContainerId}" class="list-group"></ul>
        <h5>총 주문 금액: <span id="total-order-amount-${uniqueContainerId}">0</span>원</h5>
        <button id="confirm-order-btn-${uniqueContainerId}" class="btn btn-success">주문</button>
      </div>`;

    const chatElement = document.getElementById('chat');
    chatElement.insertAdjacentHTML('beforeend', productListHtml);

    document.querySelectorAll('.select-button').forEach(button => {
      button.addEventListener('click', (event) => {
        handleSelectButtonClick(event, uniqueContainerId);
      });
    });

    document.getElementById(`confirm-order-btn-${uniqueContainerId}`).addEventListener('click', () => {
      handleConfirmOrderButtonClick(uniqueContainerId, orderId);
    });

    chatElement.scrollTop = chatElement.scrollHeight;
  };

  const handleSelectButtonClick = (event, containerId) => {
    const button = event.target;
    const productId = button.getAttribute('data-product-id');
    const productName = button.getAttribute('data-product-name');
    const productPrice = parseInt(button.getAttribute('data-product-price'));
    const quantityInput = document.getElementById(`product-quantity-${containerId}-${productId}`);
    const quantity = parseInt(quantityInput.value);
    const totalAmountElement = document.getElementById(`total-order-amount-${containerId}`);
    let totalOrderAmount = parseInt(totalAmountElement.textContent);

    const selectedProductsList = document.getElementById(`selected-products-list-${containerId}`);
    const isSelected = button.classList.contains('btn-success');

    if (isSelected) {
      button.classList.remove('btn-success');
      button.classList.add('btn-primary');
      button.textContent = '선택';

      const selectedProductItem = document.querySelector(`.selected-product[data-product-id="${productId}"]`);
      if (selectedProductItem) {
        totalOrderAmount -= selectedProductsMap[containerId][productId].productPrice * selectedProductsMap[containerId][productId].quantity;
        selectedProductItem.remove();
        delete selectedProductsMap[containerId][productId];
      }
    } else {
      button.classList.remove('btn-primary');
      button.classList.add('btn-success');
      button.textContent = '선택됨';

      selectedProductsMap[containerId][productId] = { productName, productPrice, quantity };
      totalOrderAmount += productPrice * quantity;

      const selectedItem = document.createElement('li');
      selectedItem.classList.add('selected-product', 'list-group-item');
      selectedItem.setAttribute('data-product-id', productId);
      selectedItem.innerHTML = `${productName} - ${productPrice}원 x ${quantity} = ${productPrice * quantity}원`;
      selectedProductsList.appendChild(selectedItem);
    }

    totalAmountElement.textContent = totalOrderAmount;
  };


  const handleConfirmOrderButtonClick = (containerId, orderId) => {
    const orderedProducts = Object.values(selectedProductsMap[containerId]).map(product => ({
      productName: product.productName,
      productPrice: product.productPrice,
      quantity: product.quantity,
    }));

    if (orderedProducts.length > 0) {
      const data = {
        userId: userId,
        orderedProducts: orderedProducts,
        datetime: new Date().toISOString(),
        message: orderId ? 'change_order' : 'create_order',
        orderId: orderId || null,
      };

      socket.send(JSON.stringify(data));

      const confirmOrderButton = document.getElementById(`confirm-order-btn-${containerId}`);
      confirmOrderButton.textContent = '주문 완료';
      confirmOrderButton.classList.remove('btn-success');
      confirmOrderButton.classList.add('btn-secondary');
      confirmOrderButton.disabled = true;
    }
  };

  const handleOrderClick = (order) => {
    if (selectedOrderId !== null) {
      console.error('다른 주문을 선택할 수 없습니다.');
      return;
    }
    setSelectedOrderId(order.id);
    setSelectedOrder(order);

    const data = {
      orderDetails: order,
      message: null,
      userId: userId,
      datetime: new Date().toISOString(),
      orderId: order.id
    };
    socket.send(JSON.stringify(data));

    const selectedOrderMessage = {
      userId: 'system',
      message: '선택한 주문',
      datetime: new Date().toISOString(),
      orderDetails: order
    };
    setMessages((prevMessages) => [...prevMessages, selectedOrderMessage]);

  };


  const renderRecentOrders = (recentOrders) => {
    if (!recentOrders || recentOrders.length === 0) return null;
    return (
      <div className='recent-orders'>
        <strong>주문 내역</strong>
        <ul className='list-group'>
          {recentOrders.map((order, index) => (
            <li 
              key={index} 
              className={`list-group-item order-item ${selectedOrderId === order.id ? 'selected' : ''}`}
              onClick={() => handleOrderClick(order)}
            >
              Order ID: {order.id}, Status: {order.order_status}, Created At: {order.created_at}
              <br />
              Items:
              <ul>
                {order.items.map((item, i) => (
                  <li key={i}>{item.product_name} - Quantity: {item.quantity}, Price: {item.price}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  const renderOrderDetails = (order) => {
    return (
      <div className='selected-order'>
        <strong>선택한 주문</strong>
        <p>Order ID: {order.id}, Status: {order.order_status}, Created At: {order.created_at}</p>
        <ul>
          {order.items.map((item, i) => (
            <li key={i}>{item.product_name} - Quantity: {item.quantity}, Price: {item.price}</li>
          ))}
        </ul>
      </div>
    );
  };

  const renderMessages = () => {
    return messages.map((msg, index) => {
      const isUserMessage = msg.userId === userId;
      const name = isUserMessage ? user.username || userId : '주문봇';
      const datetime = new Date(msg.datetime).toLocaleString("ko-KR", { hour: "numeric", minute: "numeric", hour12: true });

      return (
        <div key={index} className={`message ${isUserMessage ? 'me' : 'other'}`}>
          <strong>{name}</strong>
          <span className='date'>{datetime}</span><br />
          <span className='message-content'>{msg.message}</span>
          {msg.recent_orders && renderRecentOrders(msg.recent_orders)}
          {msg.orderDetails && renderOrderDetails(msg.orderDetails)}
        </div>
      );
    });
  };
  

  const displayFetchedOrders = (orders, chatElement, orderChangeType) => {
    const ordersList = document.createElement('ul');
    ordersList.classList.add('list-group');

    orders.forEach((order, index) => {
      const orderItem = document.createElement('li');
      orderItem.classList.add('list-group-item');

      let statusText = order.order_status;
      if (statusText === 'order_canceled') {
        statusText = '주문 취소됨';
      } else if (statusText === 'payment_completed') {
        statusText = '결제 완료';
      } else if (statusText === '주문 변경') {
        statusText = '주문 변경';
      } else if (statusText === 'order') {
        statusText = '주문 완료';
      }

      orderItem.innerHTML = `
        <strong>주문 ${index + 1}</strong><br>
        주문 번호: ${order.id}<br>
        주문 상태: ${statusText}<br>
        생성일시: ${new Date(order.created_at).toLocaleString('ko-KR')}<br>
        최근 업데이트: ${new Date(order.updated_at).toLocaleString('ko-KR')}<br>
        <strong>주문 상품 목록:</strong><br>
        <ul>
          ${order.items.map((item, idx) => `
            <li>상품 이름: ${item.product_name}, 수량: ${item.quantity}, 가격: ${item.price}원</li>
          `).join('')}
        </ul>
      `;

      if (orderChangeType) {
        const changeOrderButton = document.createElement('button');
        changeOrderButton.classList.add('btn', 'btn-danger', 'mt-2');
        changeOrderButton.textContent = orderChangeType === "order_changed" ? '주문 변경' : '주문 취소';

        changeOrderButton.addEventListener('click', () => {
          const message = {
            message: orderChangeType,
            userId: userId,
            orderId: order.id
          };
          socket.send(JSON.stringify(message));
        });

        orderItem.appendChild(changeOrderButton);
      }

      ordersList.appendChild(orderItem);
    });

    const orderMessageDiv = document.createElement('div');
    orderMessageDiv.classList.add('message', 'other');
    orderMessageDiv.innerHTML = `<strong>주문 목록</strong><br>`;
    orderMessageDiv.appendChild(ordersList);

    chatElement.appendChild(orderMessageDiv);
    chatElement.scrollTop = chatElement.scrollHeight;
  };

  return (
    <div>
      <div id="chat" className="border p-3 mb-3" style={{ height: '500px', overflowY: 'auto' }} ref={chatRef}>
        {renderMessages()}
   
      </div>
      <form id="chat-input" className="input-group mb-3" onSubmit={handleSubmit}>
        <input
          type="text"
          className="form-control"
          style={{ width: '80%' }}
          placeholder="메시지를 입력하세요"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
        <button type="submit" className="btn btn-primary">전송</button>
      </form>
      <div>
        <p>WebSocket 연결 상태: {socketOpen ? '연결됨' : '닫힘'}</p>
      </div>
    </div>
  );
};

export default Chat;











