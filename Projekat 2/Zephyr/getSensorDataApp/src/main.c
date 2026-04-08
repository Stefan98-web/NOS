#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/device.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/drivers/gpio.h>

BUILD_ASSERT(DT_NODE_HAS_COMPAT(DT_CHOSEN(zephyr_console), zephyr_cdc_acm_uart),
	     "Console device is not ACM CDC UART device");

int main(void)
{
    //USB serial output
	const struct device *const dev = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));

	uint32_t dtr = 0;

	while (!dtr) {
		uart_line_ctrl_get(dev, UART_LINE_CTRL_DTR, &dtr);
		k_sleep(K_MSEC(100));
	}

    //I2C
    const struct device *i2c = DEVICE_DT_GET(DT_NODELABEL(i2c1));

    if (!device_is_ready(i2c)) {
        printk("I2C not ready\n");
        return 0;
    }

    //LED
    static const struct gpio_dt_spec led = GPIO_DT_SPEC_GET(DT_ALIAS(led2), gpios);
    static const struct gpio_dt_spec ledRed = GPIO_DT_SPEC_GET(DT_ALIAS(led0), gpios);

    if (!device_is_ready(led.port) || !device_is_ready(ledRed.port)) {
        printk("LED not ready\n");
        return 0;
    }

    gpio_pin_configure_dt(&led, GPIO_OUTPUT_INACTIVE);
    gpio_pin_configure_dt(&ledRed, GPIO_OUTPUT_INACTIVE);

    //accel ON
    /* CTRL_REG6_XL (0x20) - accel enable */
    i2c_reg_write_byte(i2c, 0x6b, 0x20, 0x60);  
    // 0x60 = 119 Hz, enable X/Y/Z

    //gyro ON
    /* CTRL_REG1_G (0x10) - gyro enable */
    i2c_reg_write_byte(i2c, 0x6b, 0x10, 0x60);  
    

    //mag ON
    /* CTRL_REG1_M (0x20) - enable mag, high performance */
    i2c_reg_write_byte(i2c, 0x1E, 0x20, 0x70);

    /* CTRL_REG2_M (0x21) - ±4 gauss */
    i2c_reg_write_byte(i2c, 0x1E, 0x21, 0x00);

    /* CTRL_REG3_M (0x22) - continuous mode */
    i2c_reg_write_byte(i2c, 0x1E, 0x22, 0x00);


    k_sleep(K_MSEC(100));

    //accel
    uint8_t bufA[6];
    int16_t ax, ay, az;

    //mag
    uint8_t bufM[6];
    int16_t mx, my, mz;

    //gyro
    uint8_t bufG[6];
    int16_t gx, gy, gz;

    int32_t gx_fix = 0, gy_fix = 0, gz_fix = 0;

    gpio_pin_toggle_dt(&ledRed);

    //gyro calibration
    for (int i = 0; i < 1000; i++) {
        i2c_burst_read(i2c, 0x6b, 0x18, bufG, 6);

        gx = (int16_t)(bufG[1] << 8 | bufG[0]);
        gy = (int16_t)(bufG[3] << 8 | bufG[2]);
        gz = (int16_t)(bufG[5] << 8 | bufG[4]);

        gx_fix += gx;
        gy_fix += gy;
        gz_fix += gz;

        k_sleep(K_MSEC(5));
    }

    gx_fix = gx_fix / 1000;
    gy_fix = gy_fix / 1000;
    gz_fix = gz_fix / 1000;

    gpio_pin_toggle_dt(&ledRed);

    //read sensors data
	while (1) {
        gpio_pin_toggle_dt(&led);

        i2c_burst_read(i2c, 0x6b, 0x28, bufA, 6);

        ax = (int16_t)(bufA[1] << 8 | bufA[0]);
        ay = (int16_t)(bufA[3] << 8 | bufA[2]);
        az = (int16_t)(bufA[5] << 8 | bufA[4]);

        i2c_burst_read(i2c, 0x1E, 0x28, bufM, 6);

        mx = (int16_t)(bufM[1] << 8 | bufM[0]);
        my = (int16_t)(bufM[3] << 8 | bufM[2]);
        mz = (int16_t)(bufM[5] << 8 | bufM[4]);

        i2c_burst_read(i2c, 0x6b, 0x18, bufG, 6);

        gx = (int16_t)(bufG[1] << 8 | bufG[0]);
        gy = (int16_t)(bufG[3] << 8 | bufG[2]);
        gz = (int16_t)(bufG[5] << 8 | bufG[4]);

        printk("{\"acc\":{\"x\":%d,\"y\":%d,\"z\":%d},\"mag\":{\"x\":%d,\"y\":%d,\"z\":%d},\"gyro\":{\"x\":%d,\"y\":%d,\"z\":%d}}\n",
             ax, ay, az, mx, my, mz, gx - gx_fix, gy - gy_fix, gz - gz_fix);
        
        gpio_pin_toggle_dt(&led);

        k_sleep(K_MSEC(10)); //100Hz
	}
}