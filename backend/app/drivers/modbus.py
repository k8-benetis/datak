"""Modbus TCP/RTU async driver using pymodbus."""

from typing import Any

from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from app.drivers.base import BaseDriver, ConnectionError, ReadError, WriteError


# Sentinel to group contiguous registers for batch reading
_MAX_GAP = 16  # max gap between registers to batch them together


class ModbusDriver(BaseDriver):
    """
    Async Modbus driver supporting both TCP and RTU modes.

    Configuration for TCP:
        {
            "mode": "tcp",
            "host": "192.168.1.10",
            "port": 502,
            "slave_id": 1,
            "address": 40001,
            "count": 1,
            "register_type": "holding"  # holding, input, coil, discrete
        }

    Configuration for RTU:
        {
            "mode": "rtu",
            "port": "/dev/ttyUSB0",
            "baudrate": 9600,
            "parity": "N",
            "stopbits": 1,
            "bytesize": 8,
            "slave_id": 1,
            "address": 40001,
            "count": 1,
            "register_type": "holding"
        }
    """

    def __init__(
        self,
        sensor_id: int,
        sensor_name: str,
        config: dict[str, Any],
        registers: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ):
        super().__init__(sensor_id, sensor_name, config, **kwargs)

        self.mode = config.get("mode", "tcp")
        self.slave_id = config.get("slave_id", 1)
        self.address = config.get("address", 0)
        self.count = config.get("count", 1)
        self.register_type = config.get("register_type", "holding")

        # Multi-register support
        self._registers: list[dict[str, Any]] = registers or []

        self._client: AsyncModbusTcpClient | AsyncModbusSerialClient | None = None

    async def connect(self) -> bool:
        """Establish Modbus connection."""
        try:
            if self.mode == "tcp":
                host = self.config.get("host", "localhost")
                port = self.config.get("port", 502)
                self._client = AsyncModbusTcpClient(host=host, port=port)
                self._log.info("Connecting to Modbus TCP", host=host, port=port)

            elif self.mode == "rtu":
                serial_port = self.config.get("port", "/dev/ttyUSB0")
                baudrate = self.config.get("baudrate", 9600)
                parity = self.config.get("parity", "N")
                stopbits = self.config.get("stopbits", 1)
                bytesize = self.config.get("bytesize", 8)

                self._client = AsyncModbusSerialClient(
                    port=serial_port,
                    baudrate=baudrate,
                    parity=parity,
                    stopbits=stopbits,
                    bytesize=bytesize,
                )
                self._log.info(
                    "Connecting to Modbus RTU",
                    port=serial_port,
                    baudrate=baudrate,
                )
            else:
                raise ConnectionError(f"Unknown Modbus mode: {self.mode}")

            connected = await self._client.connect()
            return connected

        except Exception as e:
            self._log.error("Modbus connection failed", error=str(e))
            raise ConnectionError(f"Failed to connect: {e}") from e

    async def disconnect(self) -> None:
        """Close Modbus connection."""
        if self._client:
            self._client.close()
            self._client = None

    async def read(self) -> float:
        """Read single register value from Modbus device (legacy, single-register mode)."""
        if not self._client:
            raise ReadError("Not connected")

        try:
            return await self._read_register(
                self.register_type, self.address, self.count
            )
        except ModbusException as e:
            raise ReadError(f"Modbus read failed: {e}") from e

    async def _read_register(
        self, reg_type: str, address: int, count: int
    ) -> float:
        """Read a single register block and return the decoded float."""
        if reg_type == "holding":
            result = await self._client.read_holding_registers(
                address=address, count=count, slave=self.slave_id,
            )
        elif reg_type == "input":
            result = await self._client.read_input_registers(
                address=address, count=count, slave=self.slave_id,
            )
        elif reg_type == "coil":
            result = await self._client.read_coils(
                address=address, count=count, slave=self.slave_id,
            )
        elif reg_type == "discrete":
            result = await self._client.read_discrete_inputs(
                address=address, count=count, slave=self.slave_id,
            )
        else:
            raise ReadError(f"Unknown register type: {reg_type}")

        if result.isError():
            raise ReadError(f"Modbus error: {result}")

        if reg_type in ("coil", "discrete"):
            return float(result.bits[0])
        elif count == 1:
            return float(result.registers[0])
        elif count == 2:
            high = result.registers[0]
            low = result.registers[1]
            return float((high << 16) | low)
        else:
            return float(result.registers[0])

    async def read_registers(self) -> list[dict[str, Any]]:
        """
        Batch-read all configured registers for this sensor.

        Groups contiguous registers by type to minimize Modbus transactions.
        Returns a list of dicts: {register_id, address, raw_value, register_type, count}.
        """
        if not self._client:
            raise ReadError("Not connected")

        if not self._registers:
            return []

        results: list[dict[str, Any]] = []

        # Group registers by type, then by contiguous address blocks
        by_type: dict[str, list[dict]] = {}
        for reg in self._registers:
            rt = reg.get("register_type", "holding")
            by_type.setdefault(rt, []).append(reg)

        for reg_type, regs in by_type.items():
            regs_sorted = sorted(regs, key=lambda r: r["address"])

            # Group into contiguous blocks
            blocks: list[list[dict]] = []
            current_block: list[dict] = []
            prev_end = -999

            for reg in regs_sorted:
                addr = reg["address"]
                cnt = reg.get("count", 1)
                if current_block and (addr - prev_end) > _MAX_GAP:
                    blocks.append(current_block)
                    current_block = []
                current_block.append(reg)
                prev_end = addr + cnt
            if current_block:
                blocks.append(current_block)

            # Read each block in one Modbus transaction
            for block in blocks:
                start_addr = block[0]["address"]
                end_reg = block[-1]
                total_count = (end_reg["address"] - start_addr) + end_reg.get("count", 1)

                try:
                    raw_registers = await self._read_raw_block(
                        reg_type, start_addr, total_count
                    )
                except ModbusException as e:
                    raise ReadError(
                        f"Batch read failed for {reg_type} at {start_addr}: {e}"
                    ) from e

                for reg in block:
                    offset = reg["address"] - start_addr
                    cnt = reg.get("count", 1)

                    if cnt == 1:
                        val = float(raw_registers[offset])
                    elif cnt == 2:
                        val = float((raw_registers[offset] << 16) | raw_registers[offset + 1])
                    else:
                        val = float(raw_registers[offset])

                    results.append({
                        "register_id": reg["id"],
                        "name": reg.get("name", f"reg_{reg['address']}"),
                        "address": reg["address"],
                        "raw_value": val,
                        "register_type": reg_type,
                        "count": cnt,
                        "unit": reg.get("unit"),
                        "formula": reg.get("data_formula", "val"),
                        "decimal_places": reg.get("decimal_places", 2),
                    })

        return results

    async def _read_raw_block(
        self, reg_type: str, address: int, count: int
    ) -> list[int]:
        """Read a block of registers and return raw int values."""
        if reg_type == "holding":
            result = await self._client.read_holding_registers(
                address=address, count=count, slave=self.slave_id,
            )
        elif reg_type == "input":
            result = await self._client.read_input_registers(
                address=address, count=count, slave=self.slave_id,
            )
        elif reg_type == "coil":
            result = await self._client.read_coils(
                address=address, count=count, slave=self.slave_id,
            )
            return [int(b) for b in result.bits]
        elif reg_type == "discrete":
            result = await self._client.read_discrete_inputs(
                address=address, count=count, slave=self.slave_id,
            )
            return [int(b) for b in result.bits]
        else:
            raise ReadError(f"Unknown register type: {reg_type}")

        if result.isError():
            raise ReadError(f"Modbus error: {result}")

        return list(result.registers)

    def set_registers(self, registers: list[dict[str, Any]]) -> None:
        """Update the register configuration (hot-reload)."""
        self._registers = registers

    async def write(self, value: float) -> bool:
        """Write value to Modbus register."""
        if not self._client:
            raise WriteError("Not connected")

        try:
            int_value = int(value)

            if self.register_type == "holding":
                result = await self._client.write_register(
                    address=self.address,
                    value=int_value,
                    slave=self.slave_id,
                )
            elif self.register_type == "coil":
                result = await self._client.write_coil(
                    address=self.address,
                    value=bool(int_value),
                    slave=self.slave_id,
                )
            else:
                raise WriteError(f"Cannot write to {self.register_type} registers")

            if result.isError():
                raise WriteError(f"Modbus write error: {result}")

            return True

        except ModbusException as e:
            raise WriteError(f"Modbus write failed: {e}") from e
