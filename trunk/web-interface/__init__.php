<?php 

session_set_cookie_params(60 * 60 * 24 * 15); // expires in 15 days
session_start();

class Conf {
	const CONF_DIR = '';
}

?>