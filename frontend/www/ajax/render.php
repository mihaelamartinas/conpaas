<?php 
/*
 * Copyright (C) 2010-2011 Contrail consortium.                                                                                                                       
 *
 * This file is part of ConPaaS, an integrated runtime environment                                                                                                    
 * for elastic cloud applications.                                                                                                                                    
 *                                                                                                                                                                    
 * ConPaaS is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by                                                                                               
 * the Free Software Foundation, either version 3 of the License, or                                                                                                  
 * (at your option) any later version.
 * ConPaaS is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of                                                                                                     
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                                                                                                      
 * GNU General Public License for more details.                                                                                                                       
 *
 * You should have received a copy of the GNU General Public License                                                                                                  
 * along with ConPaaS.  If not, see <http://www.gnu.org/licenses/>.
 */

require_once('../__init__.php');
require_module('service');
require_module('service/factory');
require_module('ui/service');
require_module('ui/page');

if (!isset($_SESSION['uid'])) {
	throw new Exception('User not logged in');
}

$sid = $_GET['sid'];
$target = $_GET['target'];
$service_data = ServiceData::getServiceById($sid);
$service = ServiceFactory::create($service_data);

if($service->getUID() !== $_SESSION['uid']) {
    throw new Exception('Not allowed');
}

switch ($target) {
	case 'versions':
		$page = new ServicePage($service);
		echo $page->renderVersions();
		break;
	case 'instances':
		$page = new ServicePage($service);
		echo $page->renderInstances();
		break;
	default:
		echo "error: unknow target $target for rendering";
}


?>