<?php 

require_once('Service.php');
require_once('StatusLed.php');
require_once('TimeHelper.php');

function ServiceItem($data) {
	return new ServiceItem($data);
}

class ServiceItem {
	
	private $service;
	private $last = false;
	
	public function __construct(Service $service) {
		$this->service = $service;
	}
	
	public function setLast($last=true) {
		$this->last = $last;
		return $this;
	}
	
	private function renderImage() {
		return
			'<div class="icon">' 
				.'<img src="images/'.$this->service->getType().'.png" />'
			.'</div>';
	}
	
	private function renderActions() {
		if (!$this->service->isReachable()) {
			$actions = 'service is unreachable';
			if ($this->service->getState() == Service::STATE_INIT) {
				$actions .= ': <b>initializing</b>';
			}
		} else {
			$ts = strtotime($this->service->getDate());
			$actions = 'created '.TimeHelper::timeRelativeDescr($ts).' ago';
		}
		
		return
			'<div class="actions">'
				.$actions
			.'</div>';
	}
	
	private function renderStatistic($content, $note) {
		return 
			'<div class="statistic">'
				.'<div class="statcontent">'.$content.'</div>'
				.'<div class="note">'.$note.'</div>'
			.'</div>';
	}
	
	private function renderStats() {
		if (!$this->service->isReachable()) {
			if ($this->service->getState() == Service::STATE_INIT) {
				$imgsrc = 'images/throbber-on-white.gif';
			} else {
				$imgsrc = 'images/warning.png';
			}
			return $this->renderStatistic('<img src="'.$imgsrc.'" />','');
		}
		/* is reachable */
		if ($this->service->getState() == Service::STATE_INIT) {
			return '';
		}
		$monitor = $this->service->fetchHighLevelMonitoringInfo();
		$resources = 
			'<i class="text">'.$this->service->getNodesCount().'</i>'
			.'<img align="top" src="images/server-icon.png" />';
			
		if ($this->service->getType() == 'php') {
			$resptime = 
				'<i class="text">'.$monitor['avg_throughput'].'ms</i>'.
				'<img src="images/green-down.png" />';
				
			return 
				$this->renderStatistic(
					'<i class="text">'
						.$monitor['avg_error_rate'].'%'
					.'</i> <img src="images/red-up.png" />',
					'error rate')
				.$this->renderStatistic(
					'<i class="text">'.$monitor['avg_request_rate'].'/s'
					.'</i> <img src="images/blue-up.png" />', 
					'requests rate')
				.$this->renderStatistic($resptime, 'response time')
				.$this->renderStatistic($resources, 'virtual instances');
		} else if ($this->service->getType() == 'hadoop') {
			return 
				$this->renderStatistic($resources, 'virtual instances')
				.$this->renderStatistic('<i class="text">233GB</i>', 
					'data processed');
		}
	}
	
	private function renderColorTag() {
		$color_class = $this->service->getState() == Service::STATE_RUNNING ? 
			'colortag-active' : 'colortag-stopped';
		return 
			'<td class="colortag '.$color_class.'"></td>';
	}
	
	private function renderTitle() {
		if (!$this->service->isConfigurable()) {
			$title = $this->service->getName();
		} else {
			$title = 
			'<a href="configure.php?sid='.$this->service->getSID().'">'
				.$this->service->getName()
			.'</a>'; 
		}
		return
			'<div class="title">'
				.StatusLed($this->service)
				.$title
			.'</div>';
	}
	
	public function __toString() {
		$lastClass = $this->last ? 'last' : '';
		return
			'<tr class="service">'
				.$this->renderColorTag()
				.'<td class="wrapper '.$lastClass.'">' 
					.$this->renderImage()
					.'<div class="content">'
						.$this->renderTitle()
						.$this->renderActions()
					.'</div>'
					.$this->renderStats()
					.'<div class="clear"></div>'
				.'</td>'
			.'</tr>';
	}
	
}