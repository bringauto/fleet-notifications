from fleet_management_http_client_python import ( # type: ignore
    Car, CarState, CarActionState, CarActionStatus, CarStatus, Order
)

class MockApi:
    def __init__(self):
        self.cars = []
        self.car_states = []
        self.car_actions = []
        self.orders = []
        self.states_not_updating = False
        self.actions_not_updating = False

    def get_car(self, car_id: int):
        for car in self.cars:
            if car.id == car_id:
                return car
        raise Exception("Car not found")

    def get_cars(self):
        return self.cars

    def _set_cars(self, cars: list[Car]):
        self.cars = cars

    def get_car_states(self, car_id: int, last_n: int = 0):
        car_states = [state for state in self.car_states if state.car_id == car_id]
        return car_states[-last_n:] if last_n > 0 else car_states
    
    def _set_car_states(self, car_states: list[CarState]):
        self.car_states = car_states

    def get_car_action_states(self, car_id: int, last_n: int = 0):
        car_actions = [action for action in self.car_actions if action.car_id == car_id]
        return car_actions[-last_n:] if last_n > 0 else car_actions
    
    def get_order(self, car_id: int, order_id: int):
        for order in self.orders:
            if order.car_id == car_id and order.id == order_id:
                return order
        raise Exception("Order not found")
    
    def get_orders(self):
        return self.orders
            
    def _set_orders(self, orders: list[Order]):
        self.orders = orders
    
    def pause_car(self, car_id: int):
        if self.actions_not_updating:
            return
        self.car_actions.append(CarActionState(
            id=0,
            carId=car_id,
            timestamp=0,
            actionStatus=CarActionStatus.PAUSED
        ))
        if self.states_not_updating:
            return
        self.car_states.append(CarState(
            id=0,
            timestamp=0,
            status=CarStatus.IDLE,
            carId=car_id
        ))

    def unpause_car(self, car_id: int):
        if self.actions_not_updating:
            return
        self.car_actions.append(CarActionState(
            id=0,
            carId=car_id,
            timestamp=0,
            actionStatus=CarActionStatus.NORMAL
        ))
    
    def _set_car_action_states(self, car_actions: list[CarActionState]):
        self.car_actions = car_actions