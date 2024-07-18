import React, { useState, useEffect } from 'react';
const Order = ({ socketOpen, sendMessage, userId }) => {
  const [showOrderSubButtons, setShowOrderSubButtons] = useState(false);
  const [showOrderQuerySubButtons, setShowOrderQuerySubButtons] = useState(false);
  const [showChangeOrderSubButtons, setShowChangeOrderSubButtons] = useState(false);
  const [showCancelOrderSubButtons, setShowCancelOrderSubButtons] = useState(false);

  const toggleOrderSubButtons = () => setShowOrderSubButtons(!showOrderSubButtons);
  const toggleOrderQuerySubButtons = () => setShowOrderQuerySubButtons(!showOrderQuerySubButtons);
  const toggleChangeOrderSubButtons = () => setShowChangeOrderSubButtons(!showChangeOrderSubButtons);
  const toggleCancelOrderSubButtons = () => setShowCancelOrderSubButtons(!showCancelOrderSubButtons);

  const showProductList = () => {
    sendMessage({
      message: "show_products",
      userId: userId,
      datetime: new Date().toISOString()
    });
  };

  const fetchOrders = (orderType, startDate, endDate) => {
    const message = orderType === 'all' ? 'get_all_orders' : 'get_order_by_status';
    sendMessage({
      message: message,
      userId: userId,
      orderStatus: orderType !== 'all' ? orderType : undefined,
      startDate: startDate,
      endDate: endDate
    });
  };

  const handleOrderChangeOrCancel = (orderChangeType) => {
    const startDateElement = document.getElementById(`${orderChangeType}-start-date`);
    const endDateElement = document.getElementById(`${orderChangeType}-end-date`);
    const buttonElement = document.querySelector(`#${orderChangeType}-order-sub-buttons .order-btn`);

    buttonElement.addEventListener('click', () => {
      let startDate = startDateElement.value;
      let endDate = endDateElement.value;

      if (!startDate && !endDate) {
        const today = new Date();
        const oneMonthAgo = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate());
        startDate = oneMonthAgo.toISOString().split('T')[0];
        endDate = today.toISOString().split('T')[0];
      }

      const message = orderChangeType === 'change' ? 'order_to_change' : 'order_to_cancel';
      sendMessage({
        message: message,
        userId: userId,
        startDate: startDate,
        endDate: endDate
      });
    });
  };

  useEffect(() => {
    handleOrderChangeOrCancel('change');
    handleOrderChangeOrCancel('cancel');
  }, []);

  return (
    <div>
      <div className="card" style={{ width: '100%', maxWidth: '300px' }}>
        <div className="card-body">
          <h5 className="card-title text-center">직접 처리!</h5>
          <p className="card-text text-center">아래 버튼을 이용하세요</p>
        </div>
      </div>
      <div className="card my-2" style={{ width: '100%', maxWidth: '300px' }}>
        <div className="card-header">
          <button className="btn btn-primary w-100" onClick={toggleOrderSubButtons}>주문</button>
        </div>
        <div id="order-sub-buttons" className={`card-body ${showOrderSubButtons ? '' : 'd-none'}`}>
          <div className="d-grid gap-2">
            <button className="btn btn-secondary" type="button" onClick={showProductList}>메뉴 보기</button>
          </div>
        </div>
      </div>
      <div className="card my-2" style={{ width: '100%', maxWidth: '300px' }}>
        <div className="card-header">
          <button className="btn btn-primary w-100" onClick={toggleOrderQuerySubButtons}>주문 조회</button>
        </div>
        <div id="order-query-sub-buttons" className={`card-body ${showOrderQuerySubButtons ? '' : 'd-none'}`}>
          <div className="d-grid gap-2">
            <p className="text-center">&lt;기본 설정&gt;<br />1달 이내의 주문만 표시</p>
            <div className="input-group mb-3">
              <input type="text" id="start-date" className="form-control" placeholder="MM-DD" onFocus={(e) => e.target.type = 'date'} />
              <span className="input-group-text">~</span>
              <input type="text" id="end-date" className="form-control" placeholder="MM-DD" onFocus={(e) => e.target.type = 'date'} />
            </div>
            <button className="btn btn-secondary order-btn" data-order-type="all" type="button" onClick={() => fetchOrders('all', document.getElementById('start-date').value, document.getElementById('end-date').value)}>전체 주문</button>
            <button className="btn btn-secondary order-btn" data-order-type="order_changed" type="button" onClick={() => fetchOrders('order_changed', document.getElementById('start-date').value, document.getElementById('end-date').value)}>변경한 주문</button>
            <button className="btn btn-secondary order-btn" data-order-type="order_canceled" type="button" onClick={() => fetchOrders('order_canceled', document.getElementById('start-date').value, document.getElementById('end-date').value)}>취소한 주문</button>
          </div>
        </div>
      </div>
      <div className="card my-2" style={{ width: '100%', maxWidth: '300px' }}>
        <div className="card-header">
          <button className="btn btn-primary w-100" onClick={toggleChangeOrderSubButtons}>주문 변경</button>
        </div>
        <div id="change-order-sub-buttons" className={`card-body ${showChangeOrderSubButtons ? '' : 'd-none'}`}>
          <div className="d-grid gap-2">
            <p className="text-center">&lt;기본 설정&gt;<br />1달 이내의 주문만 표시</p>
            <div className="input-group mb-3">
              <input type="text" id="change-start-date" className="form-control" placeholder="MM-DD" onFocus={(e) => e.target.type = 'date'} />
              <span className="input-group-text">~</span>
              <input type="text" id="change-end-date" className="form-control" placeholder="MM-DD" onFocus={(e) => e.target.type = 'date'} />
            </div>
            <button className="btn btn-secondary order-btn" type="button">변경할 주문 선택하기</button>
          </div>
        </div>
      </div>
      <div className="card my-2" style={{ width: '100%', maxWidth: '300px' }}>
        <div className="card-header">
          <button className="btn btn-primary w-100" onClick={toggleCancelOrderSubButtons}>주문 취소</button>
        </div>
        <div id="cancel-order-sub-buttons" className={`card-body ${showCancelOrderSubButtons ? '' : 'd-none'}`}>
          <div className="d-grid gap-2">
            <p className="text-center">&lt;기본 설정&gt;<br />1달 이내의 주문만 표시</p>
            <div className="input-group mb-3">
              <input type="text" id="cancel-start-date" className="form-control" placeholder="MM-DD" onFocus={(e) => e.target.type = 'date'} />
              <span className="input-group-text">~</span>
              <input type="text" id="cancel-end-date" className="form-control" placeholder="MM-DD" onFocus={(e) => e.target.type = 'date'} />
            </div>
            <button className="btn btn-secondary order-btn" type="button">취소할 주문 선택하기</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Order;




