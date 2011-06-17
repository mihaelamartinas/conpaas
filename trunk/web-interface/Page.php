<?php 

require_once('UserData.php');

class Page {
	
	const UFILE = 'services/users.ini';
	
	protected $uid;
	protected $username;
	
	protected $browser;
	
	public static function redirect($toURL) {
		header('Location: '.$toURL);
		exit();
	}
	
	private function fetchBrowser() {
		$user_agent = $_SERVER['HTTP_USER_AGENT'];
		if (strpos($user_agent, 'Firefox') !== false) {
			$this->browser = 'firefox';
		} else if (strpos($user_agent, 'WebKit') != false) {
			$this->browser = 'webkit';
		} else {
			$this->browser = 'other';
		}
	}
	
	public function __construct() {
		if (isset($_SESSION['uid'])) {
			$this->uid = $_SESSION['uid'];
		} else {
			self::redirect('login.php');
		}
		$uinfo = UserData::getUserById($this->uid);
		if ($uinfo === false) {
			throw new Exception('User does not exist');
		}
		$this->username = $uinfo['username'];
		$this->fetchBrowser();
	}
	
	public function getBrowserClass() {
		return $this->browser;
	}
	
	public function getUsername() {
		return $this->username;
	}
	
	public function getUID() {
		return $this->uid;
	}
	
	/* render functions */
	public function renderHeader() {
		return 
			'<div class="header">'.
  				'<a id="logo" href="index.php"></a>'.
  				'<div class="user">'.
  					$this->getUsername().' | '. 
  					'<a href="javascript: void(0);" id="logout">logout</a>'.
  				'</div>'.
  				'<div class="clear"></div>'.
  			'</div>';
	}
	
}

?>