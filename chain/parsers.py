from pydantic import BaseModel, Field, conint, condecimal
from typing import List
from langchain_core.output_parsers import PydanticOutputParser
from decimal import Decimal

class OrderItem(BaseModel):
    product_name: str = Field(..., description="Name of the product")
    quantity: int = Field(..., gt=0, description="Quantity of the product")
    price: float = Field(..., description="Price of the product")


class OrderDetails(BaseModel):
    id: int = Field(description="The order ID")
    created_at: str = Field(description="The order creation date")
    order_status: str = Field(description="The current status of the order")
    items: List[OrderItem] = Field(description="The items in the order")


order_detail_parser = PydanticOutputParser(pydantic_object=OrderDetails)


class CreateOrderData(BaseModel):
    user_id: int = Field(..., description="ID of the user creating the order")
    items: List[OrderItem] = Field(..., description="List of items to order")

create_order_parser = PydanticOutputParser(pydantic_object=CreateOrderData)


class UpdateOrderStatusData(BaseModel):
    order_id: int = Field(..., description="ID of the order to update")
    new_status: str = Field(..., description="New status of the order")