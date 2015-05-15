var easyspear = angular.module('MainApp', [
	'MainApp.controllers', 'MainApp.services', 'ngRoute', 
	'wu.masonry', 'ui.bootstrap', 'angular-websocket'
]);


// Routes
easyspear.config(['$routeProvider', function($routeProvider) {
		$routeProvider.when('/list', {
			templateUrl: 'static/partials/list.html',
			controller: 'ListController'
		});
		$routeProvider.when('/followed', {
			templateUrl: 'static/partials/followed.html',
			controller: 'FollowController'
		});
		$routeProvider.when('/auction/:name', {
			templateUrl: 'static/partials/auction.html',
			controller: 'AuctionController'
		});
		$routeProvider.otherwise({
			redirectTo:'/list'
		});
}]);


// Filters
easyspear.filter('startFrom', function() {
	return function(input, start) {
		start = +start; //parse to int
		return input.slice(start);
	}
});

// Factories
easyspear.factory('TaskData', ['$websocket', function($websocket) {
	var ws = $websocket('ws://' + window.location.host + '/status');

	var tasks = {};
	ws.onOpen(function(message) {
		console.log('ws opened');
	});

	ws.onMessage(function(message) {
		console.log('got message')
		var msg = JSON.parse(message.data);
		if (tasks[msg.task_id]) {
			tasks[msg.task_id](msg); // call cb
			// remove
			delete tasks[msg.task_id];
		} else {
			console.log("Unregistered task event occured");
		}
		console.log(message);
	});

	ws.onClose(function(message) {
		console.log('ws closed')
	});

	
	return {
		register: function(task_id, cb) {
			tasks[task_id] = cb;
			//console.log("registered: " + tasks[task_id])
		}
	}
}]);

easyspear.factory('itemFactory', ['$http', function($http) {
	return {
		followToggle : function(item) {
			item.followed = !item.followed; // a white lie
			$http.get("/auction/"+ item.auction_name +"/"+ item.item_id + (item.followed ? "/follow" : "/unfollow")).success(function (data, status) {
				// oh no
			});
			return item;
		},
		updateItems : function(list, item) {
			var ret = []
			for(var i = 0; i < list.length; i++) {
				var each = list[i];
				if(each._id == item._id) {
					ret.push(item);
				} else {
					ret.push(each);
				}	
			}
			return ret;
		}
	}
}]);
	
// Directives
easyspear.directive('scrollTrigger', function($window) {
	return {
		link : function(scope, element, attrs) {
			var offset = parseInt(attrs.threshold) || 0;
			var e = jQuery(element[0]);
			var doc = jQuery(document);
			angular.element(document).bind('scroll', function() {
				if (doc.scrollTop() + $window.innerHeight + offset > e.offset().top) {
					scope.$apply(attrs.scrollTrigger);
				}
			});
		}
	}
});

easyspear.directive('timeAgo', ['NotificationService',
function(NotificationService) {
    return {
        //template: '<span>{{timeStr}}</span>',
        //replace: true,
		//scope: {
	//		test: '=date'
	//	},
        link: function(scope, element, attrs) {
            var updateTime = function(myElement, myAttrs) {
                //scope.timeStr = moment(String(attrs.timeAgo), "x").calendar();
				//console.log(element)
				//return moment(myAttrs.date, "x").calendar();
				myElement.text(moment(myAttrs.date, "x").calendar())
            }
            NotificationService.onTimeAgo(scope, element, attrs, updateTime); // subscribe
            updateTime(element, attrs);
        }
    }
}])
