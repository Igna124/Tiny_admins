#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/uaccess.h>
#include <linux/timer.h>
#include <linux/jiffies.h>
#include <linux/platform_device.h>
#include <linux/gpio/consumer.h>
#include <linux/of.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Tiny_Admins");
MODULE_DESCRIPTION("CDD para sensado de dos señales - Raspberry Pi 5");

#define DEVICE_NAME "signal_sensors"
#define CLASS_NAME "cdd_class"

static dev_t dev_num;
static struct cdev my_cdev;
static struct class *my_class = NULL;
static struct device *my_device= NULL;

static struct gpio_desc *signal_1_pin = NULL;
static struct gpio_desc *signal_2_pin = NULL;
static struct gpio_desc *generator_1_pin = NULL;
static struct gpio_desc *generator_2_pin = NULL;


static struct timer_list sensor_timer;
static int selected_signal = 1;


static void timer_callback(struct timer_list *t){


    static int counter = 0;

    

    if (counter < 5) {
        gpiod_set_value(generator_1_pin, 1);
    } else
    {
        gpiod_set_value(generator_1_pin, 0);
    }
    
    if (counter < 1) {
        gpiod_set_value(generator_2_pin, 1);
    } else
    {
        gpiod_set_value(generator_2_pin, 0);
    }


    counter++;
    if (counter >= 10)
    {
        counter = 0;
    }
    

    mod_timer(t, jiffies + (HZ / 10));
}

static ssize_t device_read(struct file *file, char __user *buffer, size_t len, loff_t *offset) {
    char data_str[32];
    int data_len;
    unsigned long not_copied;
    int pin_value = 0;


    if (*offset > 0) return 0;

    
    if (selected_signal ==1) {
        pin_value = gpiod_get_value(signal_1_pin);
    } else {
        pin_value = gpiod_get_value(signal_2_pin);
    }

    data_len = snprintf(data_str, sizeof(data_str), "%d\n", pin_value);

    if (len < data_len) return -EINVAL;

    not_copied = copy_to_user(buffer, data_str, data_len);
    if (not_copied != 0) return -EFAULT;

    *offset += data_len;
    return data_len;
}

static ssize_t device_write(struct file *file, const char __user *buffer, size_t len, loff_t *offset) {
    char k_buf[2];

    if (len == 0) return 0;

    if (copy_from_user(k_buf, buffer, 1) != 0) return -EFAULT;
    k_buf[1] = '\0';

    if (k_buf[0] == '1')
    {
        selected_signal = 1;
        pr_info("CDD: Changing to Signal 1\n");
    } else if (k_buf[0] == '2')
    {
        selected_signal = 2;
        pr_info("CDD: Changing to Signal 2\n");
    } else
    {
        pr_warn("CDD: Invalid selection (use '1' or '2')\n");
        return -EINVAL;
    }
    
    
    return len;
}

static struct file_operations fops = {
    .owner = THIS_MODULE,
    .read = device_read,
    .write = device_write,

};


static int signal_sensors_probe(struct platform_device *pdev) {

    struct device *dev = &pdev->dev;
    pr_info("CDD: Device Tree entry matched! Initializing GPIOs...\n");

    signal_1_pin = devm_gpiod_get(dev, "signal1", GPIOD_IN);
    if(IS_ERR(signal_1_pin)) {
        pr_err("CDD: Error parsing signal1-gpios\n");
        return PTR_ERR(signal_1_pin);
    }


    signal_2_pin = devm_gpiod_get(dev, "signal2", GPIOD_IN);
    if(IS_ERR(signal_2_pin)) {
        pr_err("CDD: Error parsing signal2-gpios\n");
        return PTR_ERR(signal_2_pin);
    }

    generator_1_pin = devm_gpiod_get(dev, "generator1", GPIOD_OUT_LOW);
    if(IS_ERR(generator_1_pin)) {
        pr_err("CDD: Error parsing generator1-gpios\n");
        return PTR_ERR(generator_1_pin);
    }

    generator_2_pin = devm_gpiod_get(dev, "generator2", GPIOD_OUT_LOW);
    if(IS_ERR(generator_2_pin)) {
        pr_err("CDD: Error parsing generator2-gpios\n");
        return PTR_ERR(generator_2_pin);
    }




    if (alloc_chrdev_region(&dev_num, 0, 1, DEVICE_NAME) < 0) return -1;

    cdev_init(&my_cdev, &fops);
    if (cdev_add(&my_cdev, dev_num, 1) < 0) goto unregister_chrdev;

    my_class = class_create(CLASS_NAME);
    if (IS_ERR(my_class)) goto cdev_del;

    my_device = device_create(my_class, NULL, dev_num, NULL, DEVICE_NAME);
    if (IS_ERR(my_device)) goto class_destroy;
    

    timer_setup(&sensor_timer, timer_callback, 0);
    mod_timer(&sensor_timer, jiffies + (HZ / 10));
    
    pr_info("CDD: Registered correctly in /dev/%s\n", DEVICE_NAME);
    return 0;
 
class_destroy:
    class_destroy(my_class);
cdev_del:
    cdev_del(&my_cdev);
unregister_chrdev:
    unregister_chrdev_region(dev_num, 1);
    return -1;
}


static void signal_sensors_remove(struct platform_device *pdev){
    timer_delete_sync(&sensor_timer);

    device_destroy(my_class, dev_num);
    class_destroy(my_class);
    cdev_del(&my_cdev);
    unregister_chrdev_region(dev_num, 1);

    pr_info("CDD: Module removed successfully\n");
    return ;
}

static const struct of_device_id signal_sensors_dt_ids[] = {
    { .compatible = "tiny-admins,signal-sensors", },
    { /*sentinel */ } 
};
MODULE_DEVICE_TABLE(of, signal_sensors_dt_ids);

static struct platform_driver signal_sensors_driver = {
    .probe = signal_sensors_probe,
    .remove = signal_sensors_remove,
    .driver = {
        .name = DEVICE_NAME,
        .of_match_table = signal_sensors_dt_ids,
    },
};

module_platform_driver(signal_sensors_driver);