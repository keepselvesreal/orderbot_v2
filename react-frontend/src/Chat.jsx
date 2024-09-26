import React, { useState, useEffect, useRef, useContext } from 'react';
import { UserContext } from './UserContext';
import { useWebSocket } from './useWebSocket'; 
import './Chat.css';

const selectedProductsMap = {};

const Chat = () => {
  const { user, userId } = useContext(UserContext);
  // console.log("user", user)
  const { socketOpen, sendMessage, socket } = useWebSocket();
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState('');
  const [currentConfirmMessage, setCurrentConfirmMessage] = useState(null);
  const [currentToolCallId, setCurrentToolCallId] = useState(null);
  const [selectedOrderId, setSelectedOrderId] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const chatRef = useRef(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (socket) {
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("data: ",data)

        
        if (data.message) {
          setMessages((prevMessages) => [...prevMessages, data]);
        }
        
        if (data.products) {
          console.log("products 필드 포함된 경우의 data", data)
          let orderId = null;
          if (data.order_id) {
            orderId = data.order_id
          }
          else {
              orderId = null
          }
          const productsMessage = createProductListMessage(data.products, orderId);
          setMessages((prevMessages) => [...prevMessages, productsMessage]);
        }
        if (data.fetched_orders) {
          const ordersMessage = createOrdersMessage(data.fetched_orders);
          setMessages((prevMessages) => [...prevMessages, ordersMessage]);
        }
        if (data.changeable_orders) {
          const changeableOrdersMessage = createOrdersMessage(data.changeable_orders, data.order_change_type);
          setMessages((prevMessages) => [...prevMessages, changeableOrdersMessage]);
        }
        if (typeof data.confirm_message !== 'undefined' && data.confirm_message !== null) {
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
        sender: user || 'Anonymous',
        userId: userId,
        message
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
      
      // 상태가 초기화된 후 콘솔 로그
      console.log("할당값 초기화 후\n", selectedOrderId, currentConfirmMessage, currentToolCallId);
    } else {
      console.error('Message cannot be empty.');
    }
  };


  // 지난 주문 내역 화면에 표시
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

  
  // 지난 주문 내역 중 특정 주문 선택
  const handleOrderClick = (order) => {
    if (selectedOrderId !== null) {
      console.error('다른 주문을 선택할 수 없습니다.');
      return;
    }
    setSelectedOrderId(order.id);
    setSelectedOrder(order);

    const data = {
      sender: 'system',
      message: null,
      orderId: order.id,
      orderDetails: order
    };
    socket.send(JSON.stringify(data));

    const selectedOrderMessage = {
      sender: 'system',
      message: '선택한 주문',
      orderDetails: order
    };
    setMessages((prevMessages) => [...prevMessages, selectedOrderMessage]);

    // 주문 선택 후 orderId 초기화
  setTimeout(() => {
    setSelectedOrderId(null);
    setSelectedOrder(null);
  }, 0);
  };


  // 지난 주문 내역 중 선택한 주문 화면에 표시
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


// 메시지 목록에 담기 위해 판매 상품 정보 담은 객체 생성
const createProductListMessage = (products, orderId = null) => {
  const uniqueContainerId = `selected-products-container-${Date.now()}`;
  selectedProductsMap[uniqueContainerId] = {};

  return {
    type: 'products',
    sender: 'system',
    content: products,
    orderId: orderId,
    containerId: uniqueContainerId
  };
};


// 선택 버튼 클릭 시 동작하는 함수. 해당 상품을 선택.
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


// 주문 버튼 클릭 시 동작하는 함수. 선택한 상품들을 주문. 
const handleConfirmOrderButtonClick = (containerId, orderId) => {
  console.log("handleConfirmOrderButtonClick")
  console.log("orderId: ", orderId)
  const orderedProducts = Object.values(selectedProductsMap[containerId]).map(product => ({
      productName: product.productName,
      productPrice: product.productPrice,
      quantity: product.quantity,
  }));

  if (orderedProducts.length > 0) {
      const data = {
          sender: 'system',
          userId: userId,
          message: orderId ? 'change_order' : 'create_order',
          orderId: orderId || null,
          orderedProducts: orderedProducts
      };

      console.log("Sending data:", data);

      socket.send(JSON.stringify(data));

      const confirmOrderButton = document.getElementById(`confirm-order-btn-${containerId}`);
      confirmOrderButton.textContent = '주문 완료';
      confirmOrderButton.classList.remove('btn-success');
      confirmOrderButton.classList.add('btn-secondary');
      confirmOrderButton.disabled = true;
  }
};


// 상품, 수량, 선택 버튼, 선택된 상품란을 화면에 표시
const renderProductList = (products, containerId, orderId) => {
    return (
        <div className="message other">
            <strong>메뉴 목록</strong><br />
            <ul className="list-group">
                {products.map((product, index) => (
                    <li className="list-group-item" key={index}>
                        <div className="d-flex justify-content-between align-items-center">
                            <span><strong>{product.product_name}</strong> - {product.price}원</span>
                            <input
                                type="number"
                                id={`product-quantity-${containerId}-${index}`}
                                className="form-control product-quantity"
                                style={{ width: '70px' }}
                                min="1"
                                defaultValue="1"
                                data-product-id={index}
                            />
                            <button
                                className="btn btn-primary btn-sm select-button"
                                data-product-id={index}
                                data-product-name={product.product_name}
                                data-product-price={product.price}
                                onClick={(event) => handleSelectButtonClick(event, containerId)}
                            >
                                선택
                            </button>
                        </div>
                    </li>
                ))}
            </ul>
            <div id={containerId}>
                <h5>선택된 상품</h5>
                <ul id={`selected-products-list-${containerId}`} className="list-group"></ul>
                <h5>총 주문 금액: <span id={`total-order-amount-${containerId}`}>0</span>원</h5>
                <button
                    id={`confirm-order-btn-${containerId}`}
                    className="btn btn-success"
                    onClick={() => handleConfirmOrderButtonClick(containerId, orderId)}
                >
                    주문
                </button>
            </div>
        </div>
    );
};


  // 서버에서 전달 받은 orders 정보로 메시지 목록에 삽입할 메시지 생성.
  const createOrdersMessage = (orders, orderChangeType = null) => {
    return {
      type: 'orders',
      sender: 'system',
      content: orders,
      orderChangeType: orderChangeType
    };
  };


  // 서버에서 전달 받은 지난 주문 목록을 화면에 표시.
  const renderOrders = (orders, orderChangeType) => {
    return (
      <div>
        <strong>주문 목록</strong>
        <ul className="list-group">
          {orders.map((order, index) => (
            <li key={index} className="list-group-item">
              <strong>주문 {index + 1}</strong><br />
              주문 번호: {order.id}<br />
              주문 상태: {getStatusText(order.order_status)}<br />
              생성일시: {new Date(order.created_at).toLocaleString('ko-KR')}<br />
              최근 업데이트: {new Date(order.updated_at).toLocaleString('ko-KR')}<br />
              <strong>주문 상품 목록:</strong><br />
              <ul>
                {order.items.map((item, idx) => (
                  <li key={idx}>상품 이름: {item.product_name}, 수량: {item.quantity}, 가격: {item.price}원</li>
                ))}
              </ul>
              {orderChangeType && (
                <button
                  className="btn btn-danger mt-2"
                  onClick={() => handleOrderChange(order.id, orderChangeType)}
                >
                  {orderChangeType === "order_changed" ? '주문 변경' : '주문 취소'}
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
    );
  };


  const getStatusText = (status) => {
    switch (status) {
      case 'order_canceled': return '주문 취소됨';
      case 'payment_completed': return '결제 완료';
      case '주문 변경': return '주문 변경';
      case 'order': return '주문 완료';
      default: return status;
    }
  };


  const handleOrderChange = (orderId, changeType) => {
    const message = {
      sender: "system",
      message: changeType,
      orderId: orderId
    };
    socket.send(JSON.stringify(message));
  };


  // 채팅창에 메시지를 표시
  const renderMessages = () => {
    return messages.map((msg, index) => {
      const isUserMessage = msg.sender === user;
      const name = isUserMessage ? user.username : '주문봇';
      console.log("msg.datetime: ", msg.datetime)
      const datetime = new Date().toLocaleString("ko-KR", { hour: "numeric", minute: "numeric", hour12: true });
      console.log("datetime", datetime)

      let content;
      switch (msg.type) {
        case 'products':
          content = renderProductList(msg.content, msg.containerId, msg.orderId);
          break;
        case 'orders':
          content = renderOrders(msg.content, msg.orderChangeType);
          break;
        default:
          content = <span className='message-content'>{msg.message}</span>;
      }

      return (
        <div key={index} className={`message ${isUserMessage ? 'me' : 'other'}`}>
        <strong>{name} </strong>
        <span className='date'>{datetime}</span><br />
        {content}
        {msg.recent_orders && renderRecentOrders(msg.recent_orders)}
        {msg.orderDetails && renderOrderDetails(msg.orderDetails)}
      </div>
      );
    });
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
